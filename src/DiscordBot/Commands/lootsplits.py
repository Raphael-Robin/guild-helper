import discord
from discord import app_commands
from discord.ext import commands
from src.Interfaces import ILootsplitManager, IDatabaseManager
from src.Model import Lootsplit


class LootsplitCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        lootsplit_manager: ILootsplitManager,
        database_manager: IDatabaseManager,
    ):
        self.bot = bot
        self.lootsplit_manager = lootsplit_manager
        self.database_manager = database_manager

    @app_commands.command(
        name="lootsplit", description="[Admin] Create a new loot split."
    )
    @app_commands.describe(
        item_value="Total value of items sold",
        silver="Silver collected",
        repair_cost="Total repair cost to deduct",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def lootsplit(
        self,
        interaction: discord.Interaction,
        item_value: int,
        silver: int,
        repair_cost: int,
    ):
        await interaction.response.defer()

        lootsplit = await self.lootsplit_manager.create_lootsplit(
            item_value=item_value,
            silver=silver,
            repair_cost=repair_cost,
            guild_discord_id=str(interaction.guild.id),
        )
        await self.database_manager.save_or_update_lootsplit(lootsplit)

        embed = _build_lootsplit_embed(lootsplit)
        view = LootsplitView(
            lootsplit_manager=self.lootsplit_manager,
            lootsplit=lootsplit,
            database_manager=self.database_manager,
        )
        await interaction.followup.send(embed=embed, view=view)

    @lootsplit.error
    async def lootsplit_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.", ephemeral=True
            )


def _build_lootsplit_embed(lootsplit: Lootsplit) -> discord.Embed:
    config = lootsplit.configuration
    nb_players = len(lootsplit.players)

    gross = lootsplit.item_value + lootsplit.silver
    after_repairs = gross - lootsplit.repair_cost
    tax_amount = round(after_repairs * (config.guild_tax_percent / 100))
    total_payout = after_repairs - tax_amount
    per_player = round(total_payout / nb_players) if nb_players > 0 else 0

    status = "✅ Paid Out" if lootsplit.paid_out else "⏳ Pending"
    color = discord.Color.green() if lootsplit.paid_out else discord.Color.orange()

    embed = discord.Embed(
        title=f"⚔️ Loot Split #{lootsplit.id}",
        color=color,
    )

    embed.add_field(name="Status", value=status, inline=False)

    embed.add_field(
        name="📦 Item Value", value=f"{lootsplit.item_value:,}", inline=True
    )
    embed.add_field(name="🪙 Silver", value=f"{lootsplit.silver:,}", inline=True)
    embed.add_field(
        name="🔧 Repair Cost", value=f"{lootsplit.repair_cost:,}", inline=True
    )

    embed.add_field(name="Gross", value=f"{gross:,}", inline=True)
    embed.add_field(name="After Repairs", value=f"{after_repairs:,}", inline=True)
    embed.add_field(
        name=f"Guild Tax ({config.guild_tax_percent}%)",
        value=f"{tax_amount:,}",
        inline=True,
    )

    embed.add_field(name="💰 Total Payout", value=f"**{total_payout:,}**", inline=True)
    embed.add_field(name="👥 Players", value=str(nb_players), inline=True)
    embed.add_field(
        name="💎 Per Player",
        value=f"**{per_player:,}**" if nb_players > 0 else "—",
        inline=True,
    )

    if lootsplit.players:
        names = "\n".join(p.albion_character_name for p in lootsplit.players)
        # Split into chunks if too long for one field (Discord field limit: 1024 chars)
        chunks = _chunk_text(names, 1024)
        for i, chunk in enumerate(chunks):
            label = "🧑‍🤝‍🧑 Players" if i == 0 else "🧑‍🤝‍🧑 Players (cont.)"
            embed.add_field(name=label, value=f"```{chunk}```", inline=False)

    return embed


def _chunk_text(text: str, limit: int) -> list[str]:
    chunks, current = [], []
    current_len = 0
    for line in text.split("\n"):
        if current_len + len(line) + 1 > limit:
            chunks.append("\n".join(current))
            current, current_len = [], 0
        current.append(line)
        current_len += len(line) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks


class LootsplitView(discord.ui.View):
    def __init__(
        self,
        lootsplit_manager: ILootsplitManager,
        lootsplit: Lootsplit,
        database_manager: IDatabaseManager,
    ):
        super().__init__(timeout=None)
        self.lootsplit_manager = lootsplit_manager
        self.database_manager = database_manager
        self.lootsplit = lootsplit
        self._update_buttons()

    def _update_buttons(self):
        self.pay_players_button.disabled = (
            self.lootsplit.paid_out or not self.lootsplit.players
        )
        self.add_players_button.disabled = self.lootsplit.paid_out

    async def _refresh_panel(self, interaction: discord.Interaction):
        if not self.lootsplit.id:
            raise Exception("lootsplit must have an ID here")

        self.lootsplit = await self.database_manager.get_lootsplit_by_id(
            self.lootsplit.id
        )
        self._update_buttons()
        embed = _build_lootsplit_embed(self.lootsplit)
        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="➕ Add Players", style=discord.ButtonStyle.primary)
    async def add_players_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if (
            not isinstance(interaction.user, discord.Member)
            or not interaction.user.guild_permissions.administrator
        ):
            await interaction.response.send_message("❌ Admins only.", ephemeral=True)
            return

        if not self.lootsplit.id:
            raise Exception("lootsplit must have an ID here")

        modal = AddPlayersModal(
            lootsplit_id=self.lootsplit.id,
            lootsplit_manager=self.lootsplit_manager,
            view=self,
        )
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="💰 Pay Players", style=discord.ButtonStyle.success)
    async def pay_players_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if (
            not isinstance(interaction.user, discord.Member)
            or not interaction.user.guild_permissions.administrator
        ):
            await interaction.response.send_message("❌ Admins only.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            if not self.lootsplit.id:
                raise Exception("lootsplit must have an ID here")
            await self.lootsplit_manager.add_balances(lootsplit_id=self.lootsplit.id)
        except Exception as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return

        await self._refresh_panel(interaction)

        nb_players = len(self.lootsplit.players)
        per_player = self.lootsplit_manager.get_lootsplit_value_per_player(
            self.lootsplit
        )
        await interaction.followup.send(
            f"✅ Paid out **{per_player:,}** silver to **{nb_players}** players.",
            ephemeral=True,
        )


class AddPlayersModal(discord.ui.Modal, title="Add Players to Loot Split"):
    player_names = discord.ui.TextInput(
        label="Character Names (one per line)",
        style=discord.TextStyle.paragraph,
        placeholder="PlayerOne\nPlayerTwo\nPlayerThree",
        required=True,
    )

    def __init__(
        self,
        lootsplit_id: int,
        lootsplit_manager: ILootsplitManager,
        view: LootsplitView,
    ):
        super().__init__()
        self.lootsplit_id = lootsplit_id
        self.lootsplit_manager = lootsplit_manager
        self.lootsplit_view = view

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        names = [
            name.strip()
            for name in self.player_names.value.splitlines()
            if name.strip()
        ]

        if not names:
            await interaction.followup.send(
                "❌ No valid names provided.", ephemeral=True
            )
            return

        try:
            await self.lootsplit_manager.add_players_by_name(
                character_names=names,
                lootsplit_id=self.lootsplit_id,
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to add players: {e}", ephemeral=True
            )
            return

        await self.lootsplit_view._refresh_panel(interaction)
        await interaction.followup.send(
            f"✅ Added **{len(names)}** player(s) to the split.", ephemeral=True
        )
