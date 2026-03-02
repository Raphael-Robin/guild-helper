from pydantic import BaseModel


class Player(BaseModel):
    albion_character_name: str
    albion_character_id: str
    discord_user_id: str | None = None
    balance: int = 0
    all_time_balance: int = 0
