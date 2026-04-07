"""
inference.py — Negotiation Environment Inference Script
=======================================================
Environment variables injected by the validator:
    API_BASE_URL   The LiteLLM proxy endpoint  (MUST use this)
    API_KEY        The LiteLLM proxy key        (MUST use this)
    MODEL_NAME     Model identifier for inference

Defaults:
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7860")
    MODEL_NAME   = os.getenv("MODEL_NAME",   "negotiation-agent")

STDOUT format:
    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> rewards=<r1,r2,...,rn>
"""

import os
import json
import requests

# ── Validator-injected configuration  ────────────────────────────────────────
# API_BASE_URL  → LiteLLM proxy base URL  (do NOT change or hardcode)
# API_KEY       → LiteLLM proxy key       (do NOT change or hardcode)
# MODEL_NAME    → model to use
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:7860")
API_KEY      = os.environ.get("API_KEY",      "EMPTY")          # validator injects this
MODEL_NAME   = os.environ.get("MODEL_NAME",   "negotiation-agent")

TASK_NAME  = "negotiation"
BENCHMARK  = "openenv"
MAX_ROUNDS = 6


# ── LLM call through the validator's LiteLLM proxy ───────────────────────────
# Uses raw requests so no external packages (openai SDK) are required.
# Hits  API_BASE_URL/v1/chat/completions  with  API_KEY  as Bearer token.

def llm_action(obs):
    """
    Call the LiteLLM proxy at API_BASE_URL/v1/chat/completions.
    This is the ONLY path that satisfies the validator's proxy-usage check.
    """
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    system_prompt = (
        "You are an expert negotiation agent. "
        "Your single goal is to close the deal at the highest price possible. "
        "Reply ONLY with a valid JSON object — no markdown, no extra text:\n"
        '{"price_offer": <integer>, "message": "<1-3 sentence reply to client>"}'
    )

    user_prompt = (
        f"Negotiation state — "
        f"client_budget: {obs.get('client_budget')}, "
        f"last_offer: {obs.get('last_offer')}, "
        f"round: {obs.get('round')}, "
        f"deadline: {obs.get('deadline')}. "
        f"Client message: \"{obs.get('user_message', 'Please make your offer.')}\". "
        "Respond with JSON only."
    )

    payload = {
        "model":       MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "max_tokens":  256,
        "temperature": 0.4,
    }

    # Always route through API_BASE_URL — never skip this call
    resp = requests.post(
        f"{API_BASE_URL}/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()

    raw = resp.json()["choices"][0]["message"]["content"].strip()

    # Strip accidental markdown fences
    if "```" in raw:
        raw = raw.replace("```json", "").replace("```", "").strip()

    parsed = json.loads(raw)
    price  = int(parsed["price_offer"])

    # Safety: no huge single-step swings
    last = obs.get("last_offer")
    if last is not None and abs(price - last) > 1500:
        price = int((price + last) / 2)

    return {"price_offer": price, "message": str(parsed.get("message", ""))}


# ── Fallback — only used when LLM returns unparseable output ─────────────────
# Does NOT skip the LLM call — llm_action() is always attempted first.

def rule_based_action(obs):
    budget    = obs.get("client_budget", 5000)
    last      = obs.get("last_offer")
    round_num = obs.get("round", 0)

    if last is None:
        return {"price_offer": budget + 2000,
                "message": "Based on project scope, I propose this initial offer."}
    if round_num == 1:
        return {"price_offer": last - 500,
                "message": "I can reduce slightly while maintaining quality."}
    if round_num == 2:
        return {"price_offer": last - 300,
                "message": "Finding a fair balance for both of us."}
    return {"price_offer": budget,
            "message": "Let us finalise at your budget and move forward."}


def get_action(obs):
    """
    Always calls llm_action() first so the LiteLLM proxy is hit.
    Falls back to rule_based_action() ONLY if the response cannot be parsed.
    """
    try:
        return llm_action(obs), None
    except Exception as exc:
        # Log the error but do NOT silently skip — return fallback + error msg
        return rule_based_action(obs), str(exc)


# ── Environment calls ─────────────────────────────────────────────────────────

def env_reset():
    """/reset is a GET endpoint in the FastAPI app."""
    resp = requests.get(f"{API_BASE_URL}/reset", timeout=30)
    resp.raise_for_status()
    return resp.json()


def env_step(obs, action):
    """/step is a POST endpoint."""
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

    # Print [START] immediately — before any network call —
    # so the validator always sees structured output.
    print(
        f"[START] task={TASK_NAME} env={BENCHMARK} model={MODEL_NAME}",
        flush=True,
    )

    try:
        obs = env_reset()
        obs["user_message"] = f"My budget is {obs.get('client_budget', 5000)}"

        done = False

        while not done and step_count < MAX_ROUNDS:

            # Always call the LLM through the proxy
            action, llm_error = get_action(obs)

            try:
                next_obs, reward, done, _ = env_step(obs, action)
            except Exception as step_exc:
                step_count += 1
                rewards.append(0.0)
                print(
                    f"[STEP] step={step_count} action=error "
                    f"reward=0.00 done=true error={str(step_exc)}",
                    flush=True,
                )
                success = False
                return

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
                "That seems high, can you do better?" if not done else "accepted"
            )

        success = done

    except Exception as exc:
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