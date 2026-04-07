"""
inference.py — Negotiation Environment Inference Script
=======================================================
Required environment variables:
    API_BASE_URL      Base URL of the running negotiation server.
    MODEL_NAME        Model identifier used for inference.
    HF_TOKEN          Hugging Face / API key.

Defaults:
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7860")
    MODEL_NAME   = os.getenv("MODEL_NAME",   "negotiation-agent")

STDOUT format (mandatory):
    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> rewards=<r1,r2,...,rn>

NOTE: Uses only stdlib + requests. No openai package required.
"""

import os
import json
import sys
import requests

# ── Configuration ─────────────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7860")
MODEL_NAME   = os.getenv("MODEL_NAME",   "negotiation-agent")
HF_TOKEN     = os.getenv("HF_TOKEN",     "")

TASK_NAME  = "negotiation"
BENCHMARK  = "openenv"
MAX_ROUNDS = 6


# ── Rule-based agent (zero external deps, always works) ───────────────────────

def rule_based_action(obs):
    budget    = obs.get("client_budget", 5000)
    last      = obs.get("last_offer")
    round_num = obs.get("round", 0)

    if last is None:
        return {
            "price_offer": budget + 2000,
            "message": "Based on project scope and quality, I propose this initial offer.",
        }
    if round_num == 1:
        return {
            "price_offer": last - 500,
            "message": "I can reduce slightly while maintaining the quality you need.",
        }
    if round_num == 2:
        return {
            "price_offer": last - 300,
            "message": "Finding a fair balance for both sides.",
        }
    return {
        "price_offer": budget,
        "message": "Let us finalise at your budget and move forward.",
    }


# ── LLM call via raw HTTP (OpenAI-compatible, no openai package needed) ───────

def llm_action(obs):
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {HF_TOKEN or 'EMPTY'}",
    }

    system_prompt = (
        "You are an expert negotiation agent. "
        "Respond ONLY with valid JSON: "
        '{"price_offer": <integer>, "message": "<persuasive response>"}. '
        "No markdown, no extra text outside the JSON."
    )

    user_prompt = (
        f"client_budget={obs.get('client_budget')} "
        f"last_offer={obs.get('last_offer')} "
        f"round={obs.get('round')} "
        f"deadline={obs.get('deadline')}. "
        f"Client says: {obs.get('user_message', 'Make your offer.')}. "
        "Reply with JSON only."
    )

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "max_tokens":  256,
        "temperature": 0.4,
    }

    resp = requests.post(
        f"{API_BASE_URL}/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()

    raw = resp.json()["choices"][0]["message"]["content"].strip()
    if "```" in raw:
        raw = raw.replace("```json", "").replace("```", "").strip()

    parsed = json.loads(raw)
    price  = int(parsed["price_offer"])

    last = obs.get("last_offer")
    if last is not None and abs(price - last) > 1500:
        price = int((price + last) / 2)

    return {"price_offer": price, "message": str(parsed.get("message", ""))}


def get_action(obs):
    """Try LLM first; fall back to rule-based on any failure."""
    try:
        return llm_action(obs), None
    except Exception as exc:
        return rule_based_action(obs), str(exc)


# ── Environment calls — GET /reset, POST /step ────────────────────────────────

def env_reset():
    """
    /reset is a GET endpoint in the FastAPI app (app/main.py line 25).
    Must use requests.get(), NOT requests.post().
    """
    resp = requests.get(f"{API_BASE_URL}/reset", timeout=30)
    resp.raise_for_status()
    return resp.json()


def env_step(obs, action):
    """
    /step is a POST endpoint in the FastAPI app (app/main.py line 29).
    """
    payload = {
        "observation":  obs,
        "user_message": action.get("message", ""),
        "mode":         "rule",
        "history":      [],
    }
    resp = requests.post(f"{API_BASE_URL}/step", json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    data.setdefault("action", action)
    data["action"]["price_offer"] = action["price_offer"]

    return (
        data.get("observation", obs),
        float(data.get("reward", 0.0)),
        bool(data.get("done", False)),
        {},
    )


# ── Main episode loop ─────────────────────────────────────────────────────────

def run():
    rewards    = []
    step_count = 0
    success    = False

    # [START] must be printed even if reset fails, so we do it before the try
    # that calls env_reset — but we need obs first. We guard with a two-phase
    # approach: print [START] immediately, then attempt reset inside try/except.

    print(
        f"[START] task={TASK_NAME} env={BENCHMARK} model={MODEL_NAME}",
        flush=True,
    )

    try:
        obs = env_reset()
        obs["user_message"] = f"My budget is {obs.get('client_budget', 5000)}"

        done = False

        while not done and step_count < MAX_ROUNDS:
            action, llm_error = get_action(obs)

            try:
                next_obs, reward, done, _ = env_step(obs, action)
            except Exception as step_exc:
                # Step failed — log it and terminate episode
                step_count += 1
                rewards.append(0.0)
                print(
                    f"[STEP] step={step_count} action=error "
                    f"reward=0.00 done=true error={str(step_exc)}",
                    flush=True,
                )
                success = False
                return  # goes to finally

            step_count += 1
            rewards.append(reward)

            action_str = f"offer({action['price_offer']})"
            error_str  = llm_error if llm_error else "null"

            print(
                f"[STEP] step={step_count} action={action_str} "
                f"reward={reward:.2f} done={str(done).lower()} error={error_str}",
                flush=True,
            )

            obs = next_obs
            obs["user_message"] = (
                "That seems high. Can you do better?" if not done else "accepted"
            )

        success = done

    except Exception as exc:
        # Reset failed or unexpected error — emit one STEP so validator has output
        step_count += 1
        rewards.append(0.0)
        print(
            f"[STEP] step={step_count} action=error "
            f"reward=0.00 done=true error={str(exc)}",
            flush=True,
        )
        success = False

    finally:
        rewards_str = ",".join(f"{r:.2f}" for r in rewards) if rewards else "0.00"
        print(
            f"[END] success={str(success).lower()} "
            f"steps={step_count} rewards={rewards_str}",
            flush=True,
        )


if __name__ == "__main__":
    run()