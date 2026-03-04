from abc import ABC, abstractmethod
from src.Model import Player, Guild, Alliance


class IAlbionApiManager(ABC):
    @abstractmethod
    async def get_player_id_by_name(self, player_name: str) -> str:
        pass

    @abstractmethod
    async def get_player_name_by_id(self, player_id: str) -> str:
        pass

    @abstractmethod
    async def get_player_guild(self, player: Player) -> Guild:
        pass

    @abstractmethod
    async def get_player_alliance(self, player: Player) -> Alliance:
        pass

    @abstractmethod
    async def get_guild_alliance(self, guild: Guild) -> Alliance:
        pass

    @abstractmethod
    async def get_guild_by_name(self, guild_name: str) -> Guild:
        pass

    @abstractmethod
    async def get_player_by_name(self, player_name: str) -> Player:
        pass
