import os
import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7860")
MODEL_NAME = os.getenv("MODEL_NAME", "negotiation-agent")


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

    try:
        obs = reset()

        print(f"[START] task=negotiation env=openenv model={MODEL_NAME}")

        done = False

        while not done and step_count < 5:
            msg = f"My budget is {obs.get('client_budget', 5000)}"

            result = step(obs, msg)

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

        print(
            f"[END] success={str(done).lower()} "
            f"steps={step_count} rewards={','.join(rewards)}"
        )

    except Exception as e:
        print(f"[END] success=false steps=0 rewards= error={str(e)}")


if __name__ == "__main__":
    run()