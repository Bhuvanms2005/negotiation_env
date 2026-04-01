import requests

BASE_URL = "http://localhost:7860"

def reset():
    response = requests.post(f"{BASE_URL}/reset")
    return response.json()

def step(observation, user_message="", mode="auto", history=[]):
    payload = {
        "observation": observation,
        "user_message": user_message,
        "mode": mode,
        "history": history
    }

    response = requests.post(f"{BASE_URL}/step", json=payload)
    return response.json()


# Optional test run
if __name__ == "__main__":
    obs = reset()
    print("Reset:", obs)

    result = step(obs, "my budget is 5000")
    print("Step:", result)