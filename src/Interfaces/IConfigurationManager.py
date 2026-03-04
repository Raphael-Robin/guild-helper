from abc import ABC, abstractmethod
from src.Model import Configuration


class IConfigurationManager(ABC):
    @abstractmethod
    async def get_config(self, guild_discord_server_id: str) -> Configuration:
        pass

    @abstractmethod
    async def update_config(self, config: Configuration) -> None:
        pass
