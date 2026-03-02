from pydantic import BaseModel


class Guild(BaseModel):
    name: str
    id: str
