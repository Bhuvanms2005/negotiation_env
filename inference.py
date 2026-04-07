import os
import json
import requests

# ================= CONFIG =================

LLM_BASE_URL = os.environ["API_BASE_URL"]   # MUST use this (no fallback)
API_KEY = os.environ["API_KEY"]

ENV_BASE_URL = "http://localhost:7860"      # your FastAPI backend
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-3.5-turbo")

TASK_NAME = "negotiation"
BENCHMARK = "openenv"
MAX_ROUNDS = 5

# ================= LLM CALL =================

def llm_action(obs):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": "You are a negotiation agent. Return ONLY JSON: {\"price_offer\": number, \"message\": \"text\"}"
            },
            {
                "role": "user",
                "content": f"Client budget: {obs.get('client_budget')}, last offer: {obs.get('last_offer')}"
            }
        ],
        "max_tokens": 100,
        "temperature": 0.3,
    }

    response = requests.post(
        f"{LLM_BASE_URL}/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30,
    )

    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]

    try:
        data = json.loads(content)
        return {
            "price_offer": int(data["price_offer"]),
            "message": str(data["message"])
        }, None
    except Exception as e:
        return {
            "price_offer": obs.get("client_budget", 5000),
            "message": "Let's proceed with a fair deal."
        }, str(e)

# ================= ENV CALLS =================

def env_reset():
    res = requests.post(f"{ENV_BASE_URL}/reset", timeout=30)
    res.raise_for_status()
    return res.json()

def env_step(obs, action):
    payload = {
        "observation": obs,
        "user_message": action["message"],
        "mode": "rule",
        "history": []
    }

    res = requests.post(f"{ENV_BASE_URL}/step", json=payload, timeout=30)
    res.raise_for_status()

    data = res.json()

    return (
        data.get("observation", obs),
        float(data.get("reward", 0.0)),
        bool(data.get("done", False)),
        {}
    )

# ================= MAIN LOOP =================

def run():
    rewards = []
    step_count = 0
    success = False

    print(f"[START] task={TASK_NAME} env={BENCHMARK} model={MODEL_NAME}", flush=True)

    try:
        obs = env_reset()
        done = False

        while not done and step_count < MAX_ROUNDS:

            action, error = llm_action(obs)

            obs, reward, done, _ = env_step(obs, action)

            step_count += 1
            rewards.append(reward)

            print(
                f"[STEP] step={step_count} action=offer({action['price_offer']}) "
                f"reward={reward:.2f} done={str(done).lower()} "
                f"error={error if error else 'null'}",
                flush=True
            )

        success = done

    except Exception as e:
        step_count += 1
        rewards.append(0.0)

        print(
            f"[STEP] step={step_count} action=error reward=0.00 done=true error={str(e)}",
            flush=True
        )
        success = False

    finally:
        rewards_str = ",".join(f"{r:.2f}" for r in rewards) if rewards else "0.00"

        print(
            f"[END] success={str(success).lower()} steps={step_count} rewards={rewards_str}",
            flush=True
        )

# ================= ENTRY =================

if __name__ == "__main__":
    run()