from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class AuctionBid(BaseModel):
    discord_user_id: str
    amount: int

class Auction(BaseModel):
    id: Optional[int] = Field(default=None, alias="_id")
    lootsplit_id: int
    discord_message_id: Optional[str] = None
    deadline: datetime
    min_bid: int
    bids: list[AuctionBid] = []
    winner_id: Optional[str] = None
    winning_bid: Optional[int] = None
    ended: bool = False

    model_config = {"populate_by_name": True}