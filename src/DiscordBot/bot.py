import discord
from discord.ext import commands
from src.DiscordBot.Commands.register import RegistrationCog
from src.Interfaces import IPermissionManager


def create_bot(permission_manager: IPermissionManager) -> commands.Bot:
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)

    async def setup_hook():
        await bot.add_cog(RegistrationCog(bot, permission_manager))
        await bot.tree.sync()
        print("Slash commands synced.")

    bot.setup_hook = setup_hook

    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user} (ID: {bot.user.id})")

    return bot


