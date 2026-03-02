from src.Model import Player, Configuration
from pydantic import BaseModel

class Lootsplit:
    
    configuration: Configuration
    players: list[Player]
    item_value: int
    silver: int
    repair_cost: int
    