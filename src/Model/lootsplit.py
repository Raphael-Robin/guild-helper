from typing import TYPE_CHECKING
from pydantic import BaseModel

if TYPE_CHECKING:
    from src.Model import Player, Configuration


class Lootsplit(BaseModel):
    configuration: Configuration
    players: list[Player]
    item_value: int
    silver: int
    repair_cost: int
