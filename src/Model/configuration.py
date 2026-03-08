from enum import Enum

from pydantic import BaseModel
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.Model import Guild

class SplitMode(Enum):
    guild_buys = "Guild Buys"
    sale = "sale"
    auction = "auction"

class Configuration(BaseModel):
    guild_discord_server_id: str | None = None
    guild: Guild | None = None

    # Roles Config
    admin_role_id: str | None = None
    lootsplit_manager_id: str | None = None
    balance_manager_id: str | None = None
    member_role_id: str | None = None
    ally_role_id: str | None = None
    lootsplit_buyer_role_id: str | None = None

    # Lootsplit Config
    guild_tax_percent: int = 0
    lootsplit_sale_tax_percent: int = 0
    lootsplit_sale_timer_minutes: int = 60
    split_mode: SplitMode = SplitMode.guild_buys
    auction_min_bid_percent: int = 0 
