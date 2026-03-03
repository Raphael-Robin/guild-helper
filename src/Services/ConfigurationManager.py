from src.Interfaces import IConfigurationManager, IDatabaseManager
from src.Model import Configuration


class ConfigurationManager(IConfigurationManager):
    def __init__(self, database_manager: IDatabaseManager) -> None:
        self.database_manager = database_manager

    async def get_config(self) -> Configuration:
        config = Configuration(
            guild_discord_server_id="554730364573188106"
        )
        print("test")
        return config