from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class SplitSale(BaseModel):
    id: Optional[int] = Field(default=None, alias="_id")
    lootsplit_id: int
    discord_message_id: Optional[str] = None
    deadline: datetime
    participants: list[str] = []  # discord_user_ids
    winner_id: Optional[str] = None
    ended: bool = False

    model_config = {"populate_by_name": True}
