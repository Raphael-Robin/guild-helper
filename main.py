import os
from dotenv import load_dotenv
from src.Services import PermissionManager, DatabaseManager, AlbionApiManager
from src.DiscordBot.bot import create_bot

def main():
    load_dotenv(".env")
    albion_api_manager = AlbionApiManager()
    database_manager = DatabaseManager(os.environ["MONGODB_URL"],albion_api_manager=albion_api_manager)

    permission_manager = PermissionManager(database_manager=database_manager,albion_api_manager=albion_api_manager)
    bot = create_bot(permission_manager)
    bot.run(os.environ["DISCORD_TOKEN"])


if __name__ == "__main__":
    main()
