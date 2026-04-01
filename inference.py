import os
import requests
from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7860")
MODEL_NAME = os.getenv("MODEL_NAME", "negotiation-agent")
HF_TOKEN = os.getenv("HF_TOKEN", "dummy")

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN
)


def reset():
    res = requests.post(f"{API_BASE_URL}/reset")
    return res.json()


def step(obs, message):
    payload = {
        "observation": obs,
        "user_message": message,
        "mode": "auto",
        "history": []
    }
    res = requests.post(f"{API_BASE_URL}/step", json=payload)
    return res.json()


def run():
    rewards = []
    step_count = 0

    obs = reset()

    print(f"[START] task=negotiation env=openenv model={MODEL_NAME}")

    done = False

    while not done and step_count < 5:
        user_message = f"My budget is {obs.get('client_budget', 5000)}"

        result = step(obs, user_message)

        reward = float(result.get("reward", 0))
        done = result.get("done", False)
        action = result.get("action", {}).get("price_offer", "none")

        step_count += 1
        rewards.append(f"{reward:.2f}")

        print(
            f"[STEP] step={step_count} action={action} "
            f"reward={reward:.2f} done={str(done).lower()} error=null"
        )

        obs = result.get("observation", obs)

    success = done

    print(
        f"[END] success={str(success).lower()} "
        f"steps={step_count} rewards={','.join(rewards)}"
    )


if __name__ == "__main__":
    run()