import discord
from discord.ext import commands, tasks

from src.DiscordBot.Commands import (
    SplitSaleView,
    LootsplitView,
    LeaderboardView,
    ConfirmRegistrationView,
    ConfigurationCog,
    HelpCog,
    LogsCog,
    EconomyCog,
    RegistrationCog,
    LootsplitCog,
    AuctionView
)

from src.Interfaces import (
    IPermissionManager,
    IEconomyManager,
    IDatabaseManager,
    ILootsplitManager,
    IConfigurationManager,
    IAlbionApiManager,
)
from src.utils.logger import logger



def create_bot(
    permission_manager: IPermissionManager,
    economy_manager: IEconomyManager,
    database_manager: IDatabaseManager,
    lootsplit_manager: ILootsplitManager,
    configuration_manager: IConfigurationManager,
    albion_api_manager: IAlbionApiManager,
    dev:bool = False
) -> commands.Bot:

    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="/", intents=intents)

    @tasks.loop(seconds=30)
    async def check_expired_sales():
        expired = await database_manager.get_expired_unended_sales()
        for sale, lootsplit in expired:
            if not lootsplit.discord_channel_id or not sale.discord_message_id:
                continue
            channel = bot.get_channel(int(lootsplit.discord_channel_id))
            if not channel:
                continue
            try:
                if not isinstance(channel, discord.TextChannel):
                    raise Exception("Unexpected Channel type")
                message = await channel.fetch_message(int(sale.discord_message_id))
            except discord.NotFound:
                continue

            sale_view = SplitSaleView(
                lootsplit_manager=lootsplit_manager,
                database_manager=database_manager,
                configuration_manager=configuration_manager,
                sale=sale,
                lootsplit=lootsplit,
            )
            await sale_view._end_sale_from_task(message)
        
        expired_auctions = await database_manager.get_expired_unended_auctions()
        for auction, lootsplit in expired_auctions:
            if not lootsplit.discord_channel_id or not auction.discord_message_id:
                continue
            channel = bot.get_channel(int(lootsplit.discord_channel_id))
            if not channel:
                continue
            try:
                if not isinstance(channel, discord.TextChannel):
                    raise Exception("Unexpected Channel type")
                message = await channel.fetch_message(int(auction.discord_message_id))
            except discord.NotFound:
                continue
            auction_view = AuctionView(
                lootsplit_manager=lootsplit_manager,
                database_manager=database_manager,
                auction=auction,
                lootsplit=lootsplit,
                configuration_manager=configuration_manager,
            )
            await auction_view._end_auction_from_task(message)

    @check_expired_sales.before_loop
    async def before_check():
        await bot.wait_until_ready()

    async def setup_hook():
        bot.add_view(
            LootsplitView(
                lootsplit_manager=lootsplit_manager,
                configuration_manager=configuration_manager,
                database_manager=database_manager,
                lootsplit=None,
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
        bot.add_view(
            SplitSaleView(
                lootsplit_manager=lootsplit_manager,
                database_manager=database_manager,
                configuration_manager=configuration_manager,
                sale=None,
                lootsplit=None,
            )
        )
        bot.add_view(
            AuctionView(
                lootsplit_manager=lootsplit_manager,
                database_manager=database_manager,
                auction=None,
                lootsplit=None,
                configuration_manager=configuration_manager,
        ))

        # Add cogs first so their commands are registered before syncing
        await bot.add_cog(
            ConfigurationCog(bot, configuration_manager, albion_api_manager)
        )
        await bot.add_cog(RegistrationCog(bot, permission_manager=permission_manager))
        await bot.add_cog(
            EconomyCog(bot, economy_manager, database_manager, configuration_manager)
        )
        await bot.add_cog(
            LootsplitCog(
                bot, lootsplit_manager, database_manager, configuration_manager
            )
        )
        await bot.add_cog(LogsCog(bot, database_manager, configuration_manager))
        await bot.add_cog(HelpCog(bot))

        if dev:
            dev_guild = discord.Object(id=554730364573188106)
            bot.tree.clear_commands(guild=dev_guild)
            bot.tree.copy_global_to(guild=dev_guild)
            await bot.tree.sync(guild=dev_guild)
        else:
            await bot.tree.sync()
        logger.info("Slash commands synced.")

        check_expired_sales.start()

    @bot.event
    async def on_ready():
        logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")  # type: ignore

    bot.setup_hook = setup_hook

    return bot
