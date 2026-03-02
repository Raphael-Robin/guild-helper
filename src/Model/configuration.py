from pydantic import BaseModel
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.Model import Guild

class Configuration(BaseModel):
    
    guild_discord_server_id: str
    guild: Guild

    # Roles Config
    admin_role_id: str
    member_role_id: str
    ally_role_id: str

    # Lootsplit Config
    lootsplit_buyer_role_id: str
    guild_tax_percent: int
    lootsplit_sale_timer_minutes: int