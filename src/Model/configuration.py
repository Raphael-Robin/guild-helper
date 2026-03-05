from pydantic import BaseModel
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.Model import Guild


class Configuration(BaseModel):
    guild_discord_server_id: str | None = None
    guild: Guild | None = None

    # Roles Config
    admin_role_id: str | None = None
    member_role_id: str | None = None
    ally_role_id: str | None = None

    # Lootsplit Config
    lootsplit_buyer_role_id: str | None = None
    guild_tax_percent: int = 0
    lootsplit_sale_tax_percent: int = 0
    lootsplit_sale_timer_minutes: int = 0
    guild_buys_split: bool = True
