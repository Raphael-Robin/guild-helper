from abc import ABC, abstractmethod
from src.Model import Player

class IPermissionManager(ABC):

    @abstractmethod
    def register_albion_character(self, discord_user_id: int, character_id: int) -> None:
        pass