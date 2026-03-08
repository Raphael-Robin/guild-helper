import csv
import io
import discord
from discord import app_commands
from discord.ext import commands
from src.Interfaces import IDatabaseManager, IConfigurationManager
from src.Model import Log
from src.DiscordBot.permissions import is_admin, send_permission_error

LOG_PAGE_SIZE = 10


class LogsCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        database_manager: IDatabaseManager,
        configuration_manager: IConfigurationManager,
    ):
        self.bot = bot
        self.database_manager = database_manager
        self.configuration_manager = configuration_manager

    # -------------------------------------------------------------------------
    # /logs-dump
    # -------------------------------------------------------------------------

    @app_commands.command(
        name="logs-dump", description="[Admin] Export all economy logs as a CSV file."
    )
    async def logs_dump(self, interaction: discord.Interaction):
        if not await is_admin(
            interaction=interaction, configuration_manager=self.configuration_manager
        ):
            await send_permission_error(interaction=interaction)
            return
        await interaction.response.defer(ephemeral=True)

        logs = await self.database_manager.get_all_logs()

        if not logs:
            await interaction.followup.send("❌ No logs found.", ephemeral=True)
            return

        buffer = _build_csv(logs)
        file = discord.File(fp=buffer, filename="economy_logs.csv")

        await interaction.followup.send(
            content=f"📄 Exported **{len(logs)}** log entries.",
            file=file,
            ephemeral=True,
        )

    # -------------------------------------------------------------------------
    # /logs-character
    # -------------------------------------------------------------------------

    @app_commands.command(
        name="logs-character", description="[Admin] View economy logs for a character."
    )
    @app_commands.describe(character_name="The Albion Online character name")
    async def logs_character(
        self, interaction: discord.Interaction, character_name: str
    ):
        await interaction.response.defer(ephemeral=True)

        logs = await self.database_manager.get_logs_for_character(
            albion_character_name=character_name,
            limit=LOG_PAGE_SIZE,
            offset=0,
        )

        if not logs:
            await interaction.followup.send(
                f"❌ No logs found for **{character_name}**.", ephemeral=True
            )
            return

        embed = _build_logs_embed(logs, character_name=character_name, page=0)
        view = LogsView(
            database_manager=self.database_manager,
            character_name=character_name,
            page=0,
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @logs_dump.error
    @logs_character.error
    async def logs_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.", ephemeral=True
            )


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _build_csv(logs: list[Log]) -> io.BytesIO:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Date", "Character", "Action", "Amount"])
    for log in logs:
        writer.writerow(
            [
                log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                log.player.albion_character_name,
                log.action.value,
                log.amount,
            ]
        )
    buffer.seek(0)
    return io.BytesIO(buffer.read().encode("utf-8"))


def _build_logs_embed(logs: list[Log], character_name: str, page: int) -> discord.Embed:
    embed = discord.Embed(
        title=f"Logs — {character_name}",
        color=discord.Color.blurple(),
    )

    if not logs:
        embed.description = "No logs found."
        return embed

    col_date = 16  # "YYYY-MM-DD HH:MM"
    col_action = max(len(log.action.value) for log in logs)
    col_action = max(col_action, len("Action"))
    col_amount = max(len(f"{log.amount:,}") for log in logs)
    col_amount = max(col_amount, len("Amount"))

    sep = f"{'-' * col_date}  {'-' * col_action}  {'-' * col_amount}"
    header = f"{'Date':<{col_date}}  {'Action':<{col_action}}  {'Amount':>{col_amount}}"

    rows = [
        f"{log.created_at.strftime('%Y-%m-%d %H:%M'):<{col_date}}  "
        f"{log.action.value:<{col_action}}  "
        f"{log.amount:>{col_amount},}"
        for log in logs
    ]

    embed.description = "\n".join(["```", header, sep, *rows, "```"])
    embed.set_footer(text=f"Page {page + 1}")
    return embed


# -----------------------------------------------------------------------------
# View
# -----------------------------------------------------------------------------


class LogsView(discord.ui.View):
    def __init__(
        self, database_manager: IDatabaseManager, character_name: str, page: int
    ):
        super().__init__(timeout=120)
        self.database_manager = database_manager
        self.character_name = character_name
        self.page = page
        self._update_buttons()

    def _update_buttons(self):
        self.prev_button.disabled = self.page == 0

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.page -= 1
        await self._update_logs(interaction)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.page += 1
        await self._update_logs(interaction)

    async def _update_logs(self, interaction: discord.Interaction):
        logs = await self.database_manager.get_logs_for_character(
            albion_character_name=self.character_name,
            limit=LOG_PAGE_SIZE,
            offset=self.page * LOG_PAGE_SIZE,
        )

        if not logs:
            self.page -= 1
            await interaction.response.defer()
            return

        self._update_buttons()
        self.next_button.disabled = len(logs) < LOG_PAGE_SIZE

        embed = _build_logs_embed(
            logs, character_name=self.character_name, page=self.page
        )
        await interaction.response.edit_message(embed=embed, view=self)
