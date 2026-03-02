from pydantic import BaseModel
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.Model import Player, Action


class Log(BaseModel):
    player: Player
    action: Action
    amount: int
