from abc import ABC, abstractmethod
from src.Model import Player, Guild, Alliance


class IAlbionApiManager(ABC):
    @abstractmethod
    async def get_player_id_by_name(self, player_name: str) -> str:
        pass

    @abstractmethod
    async def get_player_guild_id(self, Player: Player) -> str:
        pass

    @abstractmethod
    async def is_player_in_guild(self, player: Player, guild: Guild) -> bool:
        pass

    @abstractmethod
    async def is_player_in_alliance(self, player: Player, guild: Alliance) -> bool:
        pass
