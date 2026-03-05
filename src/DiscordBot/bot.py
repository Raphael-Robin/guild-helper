import discord
from discord.ext import commands
from src.DiscordBot.Commands.help import HelpCog
from src.DiscordBot.Commands.logs import LogsCog
from src.DiscordBot.Commands.register import ConfirmRegistrationView, RegistrationCog
from src.DiscordBot.Commands.economy import EconomyCog, LeaderboardView
from src.DiscordBot.Commands.lootsplits import LootsplitCog, LootsplitView
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
    bot = commands.Bot(command_prefix="/", intents=intents)

    async def setup_hook():
        bot.add_view(
            LootsplitView(
                lootsplit_manager=lootsplit_manager,
                lootsplit=None,  # see note below
                database_manager=database_manager,
            )
        )
        bot.add_view(
            ConfirmRegistrationView(
                discord_user_id="",
                character_name="",
                permission_manager=permission_manager,
                force=False,
            )
        )
        bot.add_view(
            LeaderboardView(
                economy_manager=economy_manager,
                page=0,
                alltime=False,
            )
        )

        await bot.add_cog(RegistrationCog(bot, permission_manager=permission_manager))
        await bot.add_cog(EconomyCog(bot, economy_manager, database_manager))
        await bot.add_cog(
            LootsplitCog(
                bot,
                lootsplit_manager,
                database_manager,
            )
        )
        await bot.add_cog(
            ConfigurationCog(
                bot,
                configuration_manager,
                albion_api_manager,
            )
        )
        await bot.add_cog(LogsCog(bot, database_manager))
        await bot.add_cog(HelpCog(bot))

        # dev_guild = discord.Object(id=554730364573188106)
        # bot.tree.copy_global_to(guild=dev_guild)
        # await bot.tree.sync(guild=dev_guild)
        await bot.tree.sync()
        print("Slash commands synced.")

    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user} (ID: {bot.user.id})")  # type: ignore

    bot.setup_hook = setup_hook

    return bot
