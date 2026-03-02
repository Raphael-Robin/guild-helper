from src.Model import Guild
from pydantic import BaseModel

class Configuration(BaseModel):
    
    guild_discord_server_id: int
    guild: Guild

    # Roles Config
    admin_role_id: int
    member_role_id: int
    ally_role_id: int

    # Lootsplit Config
    lootsplit_buyer_role_id: int
    guild_tax_percent: int
    lootsplit_sale_timer_minutes: int