from src.Model import Player, Action
from pydantic import BaseModel

class Log(BaseModel):
    player: Player 
    action: Action 
    amount: int