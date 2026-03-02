import discord
from discord.ext import commands

from dotenv import dotenv_values
import logging


async def start_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    try:
        token = dotenv_values("./.env")["TOKEN"]
        if not token:
            raise ValueError()
    except ValueError:
        logging.error("Failed to start bot. Missing token in .env file")
        return
    else:
        await bot.start(token=token)
