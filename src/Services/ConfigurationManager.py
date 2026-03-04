from src.Interfaces import IConfigurationManager, IDatabaseManager
from src.Model import Configuration


class ConfigurationManager(IConfigurationManager):
    def __init__(self, database_manager: IDatabaseManager) -> None:
        self.database_manager = database_manager

    async def get_config(self, guild_discord_server_id: str) -> Configuration:
        return await self.database_manager.get_configuration(guild_discord_server_id)

    async def update_config(self, config: Configuration) -> None:
        await self.database_manager.save_or_update_configuration(config)
