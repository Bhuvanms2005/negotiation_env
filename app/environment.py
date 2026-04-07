from app.tasks import tasks
from app.grader import grade
from app.models import Observation
import random

class NegotiationEnv:
    def __init__(self):
        self.task = None
        self.round = 0
        self.done = False
        self.client_counter = None

    def reset(self):
        self.task = random.choice(tasks)
        self.round = 0
        self.done = False
        self.client_counter = self.task["client_budget"]

        return Observation(
            client_budget=self.client_counter,
            deadline=self.task["deadline"],
            last_offer=None,
            round=self.round
        ).dict()

    def step(self, action):
        self.round += 1

        ai_offer = action["price_offer"]

        if ai_offer > self.client_counter:
            self.client_counter += int((ai_offer - self.client_counter) * 0.3)
        else:
            self.client_counter -= int((self.client_counter - ai_offer) * 0.2)

        if self.client_counter < self.task["client_budget"]:
            self.client_counter = self.task["client_budget"]

        reward = grade(action, self.task, self.round)

        if abs(ai_offer - self.client_counter) <= 300:
            self.done = True
            # Clamp strictly: adding 0.3 could push to 1.0
            reward = min(reward + 0.3, 0.99)

        if self.round >= 6:
            self.done = True

        obs = Observation(
            client_budget=self.client_counter,
            deadline=self.task["deadline"],
            last_offer=ai_offer,
            round=self.round
        ).dict()

        return obs, reward, self.done, {}

    def state(self):
        return {
            "task": self.task,
            "round": self.round,
            "done": self.done
        }
