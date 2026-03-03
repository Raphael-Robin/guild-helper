from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.Model import Player, Action


class Log(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    player: Player
    action: Action
    amount: int
