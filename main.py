import os
from dotenv import load_dotenv
from src.Services import PermissionManager, DatabaseManager, AlbionApiManager, EconomyManager, LogManager, LootsplitManager, ConfigurationManager
from src.DiscordBot.bot import create_bot


def main():
    load_dotenv(".env")
    albion_api_manager = AlbionApiManager()
    database_manager = DatabaseManager(
        os.environ["MONGODB_URL"], albion_api_manager=albion_api_manager
    )

    permission_manager = PermissionManager(
        database_manager=database_manager, albion_api_manager=albion_api_manager
    )
    # log_manager = LogManager(database_manager=database_manager)
    economy_manager = EconomyManager(database_manager=database_manager, logger=None)
    configuration_manager = ConfigurationManager(database_manager=database_manager)
    lootsplit_manager = LootsplitManager(configuration_manager=configuration_manager,database_manager=database_manager,economy_manager=economy_manager)
    bot = create_bot(permission_manager, economy_manager=economy_manager,database_manager=database_manager, lootsplit_manager=lootsplit_manager)
    bot.run(os.environ["DISCORD_TOKEN"])

    


if __name__ == "__main__":
    main()
