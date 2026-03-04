import discord
from discord.ext import commands
from src.DiscordBot.Commands.register import RegistrationCog
from src.DiscordBot.Commands.economy import EconomyCog
from src.DiscordBot.Commands.lootsplits import LootsplitCog
from src.DiscordBot.Commands.configuration import ConfigurationCog
from src.Interfaces import (
    IPermissionManager,
    IEconomyManager,
    IDatabaseManager,
    ILootsplitManager,
    IConfigurationManager,
    IAlbionApiManager,
)


def create_bot(
    permission_manager: IPermissionManager,
    economy_manager: IEconomyManager,
    database_manager: IDatabaseManager,
    lootsplit_manager: ILootsplitManager,
    configuration_manager: IConfigurationManager,
    albion_api_manager: IAlbionApiManager,
) -> commands.Bot:

    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)

    async def setup_hook():
        await bot.add_cog(RegistrationCog(bot, permission_manager=permission_manager))
        await bot.add_cog(
            EconomyCog(
                bot, economy_manager=economy_manager, database_manager=database_manager
            )
        )
        await bot.add_cog(
            LootsplitCog(
                bot,
                lootsplit_manager=lootsplit_manager,
                database_manager=database_manager,
            )
        )
        await bot.add_cog(
            ConfigurationCog(
                bot,
                configuration_manager=configuration_manager,
                albion_api_manager=albion_api_manager,
            )
        )

        await bot.tree.sync()
        print("Slash commands synced.")

    bot.setup_hook = setup_hook

    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user} (ID: {bot.user.id})")  # type: ignore

    return bot
