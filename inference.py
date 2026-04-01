"""
inference.py — Negotiation Environment Inference Script
=======================================================
Required environment variables:
    API_BASE_URL        The base URL of the running negotiation FastAPI server.
    MODEL_NAME          The model identifier used for inference.
    HF_TOKEN            Your Hugging Face / API key (passed as Bearer token).
    LOCAL_IMAGE_NAME    Docker image name (if using from_docker_image()).

Defaults:
    API_BASE_URL  = os.getenv("API_BASE_URL", "http://localhost:7860")
    MODEL_NAME    = os.getenv("MODEL_NAME", "negotiation-agent")

STDOUT format (mandatory):
    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> rewards=<r1,r2,...,rn>
"""

import os
import sys
import json

from openai import OpenAI

# ── Environment configuration ────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7860")
MODEL_NAME   = os.getenv("MODEL_NAME",   "negotiation-agent")
HF_TOKEN     = os.getenv("HF_TOKEN",     "")

TASK_NAME  = "negotiation"
BENCHMARK  = "openenv"
MAX_ROUNDS = 6          # matches environment hard cap (env.step: round >= 6 → done)

# ── OpenAI-compatible client pointed at the inference endpoint ───────────────
client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN or "EMPTY",   # some endpoints require a non-empty key
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def build_system_prompt() -> str:
    return (
        "You are an expert negotiation agent. "
        "Your goal is to close a deal at the highest possible price while "
        "staying within the client's acceptable range. "
        "Respond ONLY with valid JSON in this exact schema:\n"
        '{"price_offer": <integer>, "message": "<3-5 sentence persuasive response>"}\n'
        "Rules:\n"
        "- Never drop the price by more than 500 in a single step.\n"
        "- Justify your price with quality and value arguments.\n"
        "- If the gap between your offer and the client budget is ≤ 300, converge and close the deal.\n"
        "- Do NOT include markdown, code fences, or any text outside the JSON object."
    )


def build_user_prompt(obs: dict) -> str:
    return (
        f"Current negotiation state:\n"
        f"  client_budget : {obs.get('client_budget')}\n"
        f"  last_offer    : {obs.get('last_offer')}\n"
        f"  round         : {obs.get('round')}\n"
        f"  deadline      : {obs.get('deadline')}\n\n"
        f"Client says: \"{obs.get('user_message', 'Please make your offer.')}\"\n\n"
        "Respond with JSON only."
    )


def llm_action(obs: dict) -> dict:
    """
    Call the LLM via the OpenAI-compatible client and return an action dict
    with keys: price_offer (int) and message (str).
    Falls back to a simple rule-based action on any failure.
    """
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user",   "content": build_user_prompt(obs)},
    ]

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        max_tokens=512,
        temperature=0.4,
    )

    raw = response.choices[0].message.content.strip()

    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.strip("`").strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()

    parsed = json.loads(raw)

    price   = int(parsed["price_offer"])
    message = str(parsed.get("message", ""))

    # Safety guard: no huge single-step swings
    last = obs.get("last_offer")
    if last is not None and abs(price - last) > 1500:
        price = int((price + last) / 2)

    return {"price_offer": price, "message": message}


def rule_based_action(obs: dict) -> dict:
    """Deterministic fallback when the LLM call fails."""
    budget    = obs.get("client_budget", 5000)
    last      = obs.get("last_offer")
    round_num = obs.get("round", 0)

    if last is None:
        offer = budget + 2000
        msg   = ("Based on the project scope and quality expectations, "
                 "I propose this initial offer to ensure excellent delivery.")
    elif round_num == 1:
        offer = last - 500
        msg   = "I can reduce slightly while maintaining the quality you need."
    elif round_num == 2:
        offer = last - 300
        msg   = "I'm trying to find a fair balance for both of us."
    else:
        offer = budget
        msg   = "Let's finalise at your budget and move forward together."

    return {"price_offer": offer, "message": msg}


def get_action(obs: dict) -> tuple[dict, str | None]:
    """
    Returns (action_dict, error_str_or_None).
    Tries the LLM first; falls back to rule-based on exception.
    """
    try:
        action = llm_action(obs)
        return action, None
    except Exception as exc:
        return rule_based_action(obs), str(exc)


# ── Environment interaction via the FastAPI server ───────────────────────────

def env_reset() -> dict:
    """POST /reset and return the initial observation."""
    import requests
    resp = requests.post(f"{API_BASE_URL}/reset", timeout=30)
    resp.raise_for_status()
    return resp.json()


def env_step(obs: dict, action: dict) -> tuple[dict, float, bool, dict]:
    """
    POST /step with the current observation and action.
    Returns (next_obs, reward, done, info).
    """
    import requests
    payload = {
        "observation":  obs,
        "user_message": action.get("message", ""),
        "mode":         "rule",     # we drive the action ourselves
        "history":      [],
    }
    resp = requests.post(f"{API_BASE_URL}/step", json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # The server may return the action it computed; we prefer our own action's
    # price_offer for the STEP log, so we inject it back into the response.
    data.setdefault("action", action)
    data["action"]["price_offer"] = action["price_offer"]

    return (
        data.get("observation", obs),
        float(data.get("reward", 0.0)),
        bool(data.get("done", False)),
        {},
    )


# ── Main episode loop ─────────────────────────────────────────────────────────

def run() -> None:
    rewards:    list[float] = []
    step_count: int         = 0
    success:    bool        = False

    try:
        obs = env_reset()

        # Inject a neutral opening user message
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

            # Format action string compactly
            action_str = f"offer({action['price_offer']})"
            error_str  = llm_error if llm_error else "null"

            print(
                f"[STEP] step={step_count} action={action_str} "
                f"reward={reward:.2f} done={str(done).lower()} "
                f"error={error_str}",
                flush=True,
            )

            # Prepare next observation with a contextual user message
            obs = next_obs
            obs["user_message"] = (
                "That seems high. Can you do better?"
                if not done
                else "accepted"
            )

        success = done

    except Exception as exc:
        # Emit a final STEP for visibility if we crash mid-episode
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