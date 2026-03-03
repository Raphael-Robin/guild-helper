from typing import TYPE_CHECKING, Optional
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.Model import Player, Configuration


class Lootsplit(BaseModel):
    id: Optional[int] = Field(alias="_id", default=None)
    configuration: Configuration
    players: list[Player]
    item_value: int
    silver: int
    repair_cost: int
    paid_out: bool = False
