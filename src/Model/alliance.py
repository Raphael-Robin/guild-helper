from pydantic import BaseModel
from src.Model import Guild

class Alliance(BaseModel):

    name: str
    id: int 
    guilds: list[Guild]