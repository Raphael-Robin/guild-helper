import logging
import os
from dotenv import load_dotenv
from src.Services import (
    PermissionManager,
    DatabaseManager,
    AlbionApiManager,
    EconomyManager,
    LootsplitManager,
    ConfigurationManager,
    LogManager,
)
from src.DiscordBot.bot import create_bot
from argparse import ArgumentParser
from src.utils.logger import handler

def main():
    
    parser = ArgumentParser(prog="GuildHelper")
    parser.add_argument("-d", "--dev", action="store_true")
    args = parser.parse_args()
    if args.dev:
        load_dotenv("test.env")
        database_name = "guild-helper-test"
    else:
        load_dotenv(".env")
        database_name = "guild-helper"


    albion_api_manager = AlbionApiManager()
    database_manager = DatabaseManager(
        os.environ["MONGODB_URL"],
        albion_api_manager=albion_api_manager,
        database_name=database_name,
    )

    permission_manager = PermissionManager(
        database_manager=database_manager, albion_api_manager=albion_api_manager
    )
    log_manager = LogManager(database_manager=database_manager)
    economy_manager = EconomyManager(
        database_manager=database_manager, log_manager=log_manager
    )
    configuration_manager = ConfigurationManager(database_manager=database_manager)
    lootsplit_manager = LootsplitManager(
        configuration_manager=configuration_manager,
        database_manager=database_manager,
        economy_manager=economy_manager,
    )
    configuration_manager = ConfigurationManager(database_manager=database_manager)
    bot = create_bot(
        permission_manager,
        economy_manager=economy_manager,
        database_manager=database_manager,
        lootsplit_manager=lootsplit_manager,
        configuration_manager=configuration_manager,
        albion_api_manager=albion_api_manager,
        dev=args.dev
    )
    bot.run(os.environ["DISCORD_TOKEN"], log_handler=handler, log_level=logging.CRITICAL)


if __name__ == "__main__":
    main()
