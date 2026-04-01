import requests

url = "http://127.0.0.1:8000"

obs = requests.get(f"{url}/reset").json()

done = False
total = 0

while not done:
    res = requests.post(f"{url}/step", json={
        "observation": obs,
        "mode": "auto"
    }).json()

    obs = res["observation"]
    total += res["reward"]
    done = res["done"]

print("Final Score:", total)