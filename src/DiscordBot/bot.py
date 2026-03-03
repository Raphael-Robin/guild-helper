import discord
from discord.ext import commands
from src.DiscordBot.Commands.register import RegistrationCog
from src.DiscordBot.Commands.economy import EconomyCog
from src.DiscordBot.Commands.lootsplits import LootsplitCog
from src.Interfaces import IPermissionManager, IEconomyManager, IDatabaseManager, ILootsplitManager


def create_bot(permission_manager: IPermissionManager, economy_manager: IEconomyManager, database_manager: IDatabaseManager, lootsplit_manager: ILootsplitManager) -> commands.Bot:
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)

    async def setup_hook():
        await bot.add_cog(RegistrationCog(bot, permission_manager=permission_manager))
        await bot.add_cog(EconomyCog(bot, economy_manager=economy_manager, database_manager=database_manager))
        await bot.add_cog(LootsplitCog(bot, lootsplit_manager=lootsplit_manager, database_manager=database_manager))
        
        dev_guild = discord.Object(id=554730364573188106)  # replace with your server ID
        bot.tree.copy_global_to(guild=dev_guild)
        await bot.tree.sync(guild=dev_guild)
        print("Slash commands synced.")

    bot.setup_hook = setup_hook

    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user} (ID: {bot.user.id})") # type: ignore

    return bot
