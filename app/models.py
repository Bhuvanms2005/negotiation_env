from pydantic import BaseModel
from typing import Optional

class Observation(BaseModel):
    client_budget: int
    deadline: int
    last_offer: Optional[int]
    round: int

class Action(BaseModel):
    price_offer: int
    message: str

class Reward(BaseModel):
    score: float