from src.Model import Log, Action
from Interfaces.ILogManager import ILogManager
from pydantic import BaseModel

class Player(BaseModel):
    discord_user_id: int
    balance: int
    all_time_balance: int
    albion_character_id: int