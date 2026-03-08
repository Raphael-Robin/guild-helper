import asyncio
import discord
import os
from dotenv import load_dotenv

load_dotenv(".env")

GUILD_ID = 1477767599637925970


async def clear_commands():
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    async with client:
        await client.login(os.environ["DISCORD_TOKEN"])

        # Clear guild commands
        client.http.token = os.environ["DISCORD_TOKEN"]
        await client.http.bulk_upsert_guild_commands(
            client.application_id, GUILD_ID, []
        )
        print(f"✅ Cleared guild commands for {GUILD_ID}")

        # Clear global commands
        await client.http.bulk_upsert_global_commands(client.application_id, [])
        print("✅ Cleared global commands")


asyncio.run(clear_commands())
