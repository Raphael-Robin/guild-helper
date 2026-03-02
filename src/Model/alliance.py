from pydantic import BaseModel
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.Model import Guild


class Alliance(BaseModel):
    name: str
    id: str
    guilds: list[Guild]
