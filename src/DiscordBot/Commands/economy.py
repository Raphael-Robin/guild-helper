import discord
from discord import app_commands
from discord.ext import commands
from src.Interfaces import IEconomyManager, IDatabaseManager
from src.Model import Player

PAGE_SIZE = 10


class EconomyCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        economy_manager: IEconomyManager,
        database_manager: IDatabaseManager,
    ):
        self.bot = bot
        self.economy_manager = economy_manager
        self.database_manager = database_manager

    @app_commands.command(name="balance", description="Display the balance of a user.")
    @app_commands.describe(
        user="The Discord user to check the balance of (defaults to yourself)"
    )
    async def balance(
        self, interaction: discord.Interaction, user: discord.Member | None = None
    ):
        await interaction.response.defer(ephemeral=True)

        target = user or interaction.user

        players = await self.database_manager.get_players_by_discord_id(str(target.id))

        if not players:
            await interaction.followup.send(
                f"❌ No characters found for {target.mention}.", ephemeral=True
            )
            return

        total_balance = sum(p.balance for p in players)
        total_alltime = sum(p.all_time_balance for p in players)

        embed = discord.Embed(
            title=f"💰 Balance — {target.display_name}",
            color=discord.Color.gold(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        if len(players) == 1:
            embed.add_field(
                name="Character", value=players[0].albion_character_name, inline=True
            )
            embed.add_field(
                name="Balance", value=f"{players[0].balance:,}", inline=True
            )
            embed.add_field(
                name="All-Time", value=f"{players[0].all_time_balance:,}", inline=True
            )
        else:
            col_name = max(len(p.albion_character_name) for p in players)
            col_name = max(col_name, len("Character"))
            col_bal = max(len(f"{p.balance:,}") for p in players)
            col_bal = max(col_bal, len("Balance"))
            col_all = max(len(f"{p.all_time_balance:,}") for p in players)
            col_all = max(col_all, len("All-Time"))

            sep = f"{'-' * col_name}  {'-' * col_bal}  {'-' * col_all}"
            header = f"{'Character':<{col_name}}  {'Balance':>{col_bal}}  {'All-Time':>{col_all}}"

            rows = [
                f"{p.albion_character_name:<{col_name}}  {p.balance:>{col_bal},}  {p.all_time_balance:>{col_all},}"
                for p in players
            ]
            total_row = f"{'TOTAL':<{col_name}}  {total_balance:>{col_bal},}  {total_alltime:>{col_all},}"

            table = "\n".join(["```", header, sep, *rows, sep, total_row, "```"])
            embed.description = table
            embed.set_footer(text=f"Total across {len(players)} characters")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="remove-balance", description="[Admin] Remove balance from a user."
    )
    @app_commands.describe(
        user="The Discord user to remove balance from",
        amount="Amount to remove (omit to zero out the balance)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_balance(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: int | None = None,
    ):
        await interaction.response.defer(ephemeral=True)

        if amount is not None and amount <= 0:
            await interaction.followup.send(
                "❌ Amount must be a positive integer.", ephemeral=True
            )
            return
        current_balance = await self.economy_manager.get_balance(str(user.id))

        if current_balance == 0:
            await interaction.followup.send(
                f"ℹ️ {user.mention} already has a balance of 0.", ephemeral=True
            )
            return

        to_remove = amount if amount is not None else current_balance

        if to_remove > current_balance or to_remove < 0:
            await interaction.followup.send(
                f"❌ Cannot remove **{to_remove:,}** — {user.mention} only has **{current_balance:,}**.",
                ephemeral=True,
            )
            return
        
        await self.economy_manager.remove_balance(str(user.id), to_remove)

        new_balance = current_balance - to_remove
        await interaction.followup.send(
            f"✅ Removed **{to_remove:,}** from {user.mention}.\n"
            f"New balance: **{new_balance:,}**",
            ephemeral=True,
        )

    @remove_balance.error
    async def remove_balance_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.", ephemeral=True
            )

    @app_commands.command(
        name="leaderboard", description="Show players with the highest current balance."
    )
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        players = await self.economy_manager.get_players_with_highest_balance(
            PAGE_SIZE, offset=0
        )
        embed = _build_leaderboard_embed(players, page=0, alltime=False)
        view = LeaderboardView(
            economy_manager=self.economy_manager, page=0, alltime=False
        )
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(
        name="leaderboard-alltime",
        description="Show players with the highest all-time balance.",
    )
    async def leaderboard_alltime(self, interaction: discord.Interaction):
        await interaction.response.defer()
        players = await self.economy_manager.get_players_with_highest_alltime_balance(
            PAGE_SIZE, offset=0
        )
        embed = _build_leaderboard_embed(players, page=0, alltime=True)
        view = LeaderboardView(
            economy_manager=self.economy_manager, page=0, alltime=True
        )
        await interaction.followup.send(embed=embed, view=view)


def _build_leaderboard_embed(
    players: list[Player], page: int, alltime: bool
) -> discord.Embed:
    title = "All-Time Leaderboard" if alltime else "Leaderboard"
    balance_key = "all_time_balance" if alltime else "balance"

    embed = discord.Embed(title=title, color=discord.Color.gold())

    if not players:
        embed.description = "No players found."
        return embed

    col_rank = 4
    col_name = max(len(p.albion_character_name) for p in players)
    col_name = max(col_name, len("Character"))
    col_bal = max(len(f"{getattr(p, balance_key):,}") for p in players)
    col_bal = max(col_bal, len("Balance"))

    sep = f"{'-' * col_rank} {'-' * col_name} {'-' * col_bal}"

    table_lines = [
        "```",
        f"{'#':<{col_rank}} {'Character':<{col_name}} {'Balance':>{col_bal}}",
        sep,
    ]
    for i, player in enumerate(players):
        rank = page * PAGE_SIZE + i + 1
        balance_value = getattr(player, balance_key)
        table_lines.append(
            f"{f'{rank}.':<{col_rank}} {player.albion_character_name:<{col_name}} {balance_value:>{col_bal},}"
        )
    table_lines += [sep, "```"]

    embed.description = "\n".join(table_lines)
    embed.set_footer(text=f"Page {page + 1}")
    return embed


class LeaderboardView(discord.ui.View):
    def __init__(self, economy_manager: IEconomyManager, page: int, alltime: bool):
        super().__init__(timeout=120)
        self.economy_manager = economy_manager
        self.page = page
        self.alltime = alltime
        self._update_buttons()

    def _update_buttons(self):
        self.prev_button.disabled = self.page == 0

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.page -= 1
        await self.update_leaderboard(interaction)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.page += 1
        await self.update_leaderboard(interaction)

    async def update_leaderboard(self, interaction: discord.Interaction):
        offset = self.page * PAGE_SIZE
        if self.alltime:
            players = (
                await self.economy_manager.get_players_with_highest_alltime_balance(
                    PAGE_SIZE, offset
                )
            )
        else:
            players = await self.economy_manager.get_players_with_highest_balance(
                PAGE_SIZE, offset
            )

        # If next page is empty, roll back and don't update
        if not players:
            self.page -= 1 if self.page > 0 else 0
            await interaction.response.defer()
            return

        self._update_buttons()
        # Disable next if we got fewer results than a full page
        self.next_button.disabled = len(players) < PAGE_SIZE

        embed = _build_leaderboard_embed(players, self.page, self.alltime)
        await interaction.response.edit_message(embed=embed, view=self)
