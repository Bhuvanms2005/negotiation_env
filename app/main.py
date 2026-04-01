from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.environment import NegotiationEnv
from app.agent import get_action
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

env = NegotiationEnv()

def extract_budget(text):
    numbers = re.findall(r"\d+", text)
    if numbers:
        return int(numbers[0])
    return None

@app.get("/reset")
def reset():
    return env.reset()

@app.post("/step")
def step(payload: dict):
    obs = payload.get("observation", {})
    user_message = payload.get("user_message", "")
    mode = payload.get("mode", "auto")
    history = payload.get("history", [])

    if env.done:
        return {
            "observation": obs,
            "reward": 1.0,
            "done": True,
            "action": {
                "price_offer": obs.get("last_offer", obs.get("client_budget")),
                "message": "Negotiation already completed.",
                "source": "system"
            }
        }

    obs["user_message"] = user_message
    obs["history"] = history

    budget = extract_budget(user_message)
    if budget:
        obs["client_budget"] = budget
        if env.task:
            env.task["client_budget"] = budget

    msg = user_message.lower()

    accept_phrases = [
        "accept",
        "agreed",
        "deal done",
        "sounds good",
        "okay done",
        "confirmed",
        "let's proceed"
    ]

    is_accept = any(p in msg for p in accept_phrases)

    if is_accept:
        env.done = True
        return {
            "observation": obs,
            "reward": 1.0,
            "done": True,
            "action": {
                "price_offer": obs.get("last_offer", obs["client_budget"]),
                "message": "Great! Deal confirmed. Looking forward to working with you.",
                "source": "system"
            }
        }

    action = get_action(obs, mode)

    observation, reward, done, _ = env.step(action)

    if done:
        env.done = True

    return {
        "observation": observation,
        "reward": reward,
        "done": done,
        "action": action
    }

@app.get("/")
def root():
    return {"message": "API running"}