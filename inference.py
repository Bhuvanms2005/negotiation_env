import os
import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7860")
MODEL_NAME = os.getenv("MODEL_NAME", "negotiation-agent")

def reset():
    res = requests.post(f"{API_BASE_URL}/reset")
    return res.json()

def step(obs, user_message):
    payload = {
        "observation": obs,
        "user_message": user_message,
        "mode": "auto",
        "history": []
    }
    res = requests.post(f"{API_BASE_URL}/step", json=payload)
    return res.json()


def run():
    step_count = 0
    rewards = []

    obs = reset()

    print(f"[START] task=negotiation env=openenv model={MODEL_NAME}")

    done = False

    while not done and step_count < 5:
        user_message = "my budget is " + str(obs.get("client_budget", 5000))

        result = step(obs, user_message)

        action = result.get("action", {})
        reward = float(result.get("reward", 0))
        done = result.get("done", False)

        rewards.append(f"{reward:.2f}")
        step_count += 1

        print(
            f"[STEP] step={step_count} "
            f"action={action.get('price_offer')} "
            f"reward={reward:.2f} "
            f"done={str(done).lower()} "
            f"error=null"
        )

        obs = result.get("observation", obs)

    success = done

    print(
        f"[END] success={str(success).lower()} "
        f"steps={step_count} "
        f"rewards={','.join(rewards)}"
    )


if __name__ == "__main__":
    run()