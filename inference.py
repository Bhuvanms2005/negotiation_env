"""
inference.py — Negotiation Environment Inference Script
=======================================================
Required environment variables:
    API_BASE_URL        Base URL of the running negotiation server.
    MODEL_NAME          Model identifier used for inference.
    HF_TOKEN            Hugging Face / API key.
    LOCAL_IMAGE_NAME    Docker image name (if using from_docker_image()).

Defaults:
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7860")
    MODEL_NAME   = os.getenv("MODEL_NAME",   "negotiation-agent")

STDOUT format:
    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> rewards=<r1,r2,...,rn>

NOTE: Uses only stdlib + requests (no openai package required).
"""

import os
import json
import requests

# ── Configuration ─────────────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7860")
MODEL_NAME   = os.getenv("MODEL_NAME",   "negotiation-agent")
HF_TOKEN     = os.getenv("HF_TOKEN",     "")

TASK_NAME  = "negotiation"
BENCHMARK  = "openenv"
MAX_ROUNDS = 6


# ── LLM call via raw HTTP (OpenAI-compatible, no openai package needed) ───────

def llm_action(obs):
    """
    Calls any OpenAI-compatible /v1/chat/completions endpoint using
    plain requests — no openai SDK dependency required.
    """
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {HF_TOKEN or 'EMPTY'}",
    }

    system_prompt = (
        "You are an expert negotiation agent. "
        "Your goal is to close a deal at the highest possible price. "
        "Respond ONLY with valid JSON in this exact schema:\n"
        '{"price_offer": <integer>, "message": "<3-5 sentence persuasive response>"}\n'
        "Rules:\n"
        "- Never drop the price by more than 500 in a single step.\n"
        "- If the gap between your offer and the client budget is <= 300, converge and close.\n"
        "- Do NOT include markdown, code fences, or any text outside the JSON object."
    )

    user_prompt = (
        f"Current negotiation state:\n"
        f"  client_budget : {obs.get('client_budget')}\n"
        f"  last_offer    : {obs.get('last_offer')}\n"
        f"  round         : {obs.get('round')}\n"
        f"  deadline      : {obs.get('deadline')}\n\n"
        f"Client says: \"{obs.get('user_message', 'Please make your offer.')}\"\n\n"
        "Respond with JSON only."
    )

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "max_tokens":  512,
        "temperature": 0.4,
    }

    resp = requests.post(
        f"{API_BASE_URL}/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()

    raw = resp.json()["choices"][0]["message"]["content"].strip()

    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.strip("`").strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()

    parsed = json.loads(raw)
    price  = int(parsed["price_offer"])

    # Safety guard: no huge single-step swings
    last = obs.get("last_offer")
    if last is not None and abs(price - last) > 1500:
        price = int((price + last) / 2)

    return {"price_offer": price, "message": str(parsed.get("message", ""))}


# ── Rule-based fallback (zero external deps) ──────────────────────────────────

def rule_based_action(obs):
    budget    = obs.get("client_budget", 5000)
    last      = obs.get("last_offer")
    round_num = obs.get("round", 0)

    if last is None:
        return {
            "price_offer": budget + 2000,
            "message": "Based on the project scope and quality expectations, I propose this initial offer.",
        }
    if round_num == 1:
        return {
            "price_offer": last - 500,
            "message": "I can reduce slightly while maintaining the quality you need.",
        }
    if round_num == 2:
        return {
            "price_offer": last - 300,
            "message": "I am trying to find a fair balance for both of us.",
        }
    return {
        "price_offer": budget,
        "message": "Let us finalise at your budget and move forward together.",
    }


def get_action(obs):
    """Returns (action_dict, error_str_or_None). Falls back to rule-based on any LLM failure."""
    try:
        return llm_action(obs), None
    except Exception as exc:
        return rule_based_action(obs), str(exc)


# ── Environment calls ─────────────────────────────────────────────────────────

def env_reset():
    resp = requests.post(f"{API_BASE_URL}/reset", timeout=30)
    resp.raise_for_status()
    return resp.json()


def env_step(obs, action):
    payload = {
        "observation":  obs,
        "user_message": action.get("message", ""),
        "mode":         "rule",
        "history":      [],
    }
    resp = requests.post(f"{API_BASE_URL}/step", json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # Ensure our chosen price_offer is preserved in the response
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

    try:
        obs = env_reset()
        obs["user_message"] = f"My budget is {obs.get('client_budget', 5000)}"

        print(
            f"[START] task={TASK_NAME} env={BENCHMARK} model={MODEL_NAME}",
            flush=True,
        )

        done = False

        while not done and step_count < MAX_ROUNDS:
            action, llm_error = get_action(obs)
            next_obs, reward, done, _ = env_step(obs, action)

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
        step_count += 1
        rewards.append(0.0)
        print(
            f"[STEP] step={step_count} action=error reward=0.00 "
            f"done=true error={str(exc)}",
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