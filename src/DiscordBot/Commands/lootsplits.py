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

        embed = _build_lootsplit_embed(lootsplit)
        view = LootsplitView(
            lootsplit_manager=self.lootsplit_manager,
            lootsplit=lootsplit,
            database_manager=self.database_manager,
        )
        message = await interaction.followup.send(embed=embed, view=view, wait=True)
        lootsplit.discord_message_id = str(message.id)
        view.lootsplit = lootsplit
        await self.database_manager.save_or_update_lootsplit(lootsplit)

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
    sale_tax_amount = round(after_repairs * (config.lootsplit_sale_tax_percent / 100))
    guild_tax_amount = round(after_repairs * (config.guild_tax_percent / 100))
    after_taxes = after_repairs - sale_tax_amount - guild_tax_amount
    total_payout = after_taxes
    per_player = round(total_payout / nb_players) if nb_players > 0 else 0

    status = "Paid Out" if lootsplit.paid_out else "Pending"
    color = discord.Color.green() if lootsplit.paid_out else discord.Color.orange()

    embed = discord.Embed(
        title=f"Loot Split #{lootsplit.id}",
        color=color,
    )

    embed.add_field(name="Status", value=status, inline=False)
    embed.add_field(name="Item Value", value=f"{lootsplit.item_value:,}", inline=True)
    embed.add_field(name="Silver", value=f"{lootsplit.silver:,}", inline=True)
    embed.add_field(name="Repair Cost", value=f"{lootsplit.repair_cost:,}", inline=True)
    embed.add_field(name="Value Before Taxes", value=f"{after_repairs:,}", inline=True)
    embed.add_field(
        name=f"Guild Tax ({config.guild_tax_percent}%)",
        value=f"{guild_tax_amount:,}",
        inline=True,
    )
    embed.add_field(
        name=f"Sale Tax ({config.lootsplit_sale_tax_percent}%)",
        value=f"{sale_tax_amount:,}",
        inline=True,
    )
    embed.add_field(name="Total Payout", value=f"**{total_payout:,}**", inline=True)
    embed.add_field(name="Players", value=str(nb_players), inline=True)
    embed.add_field(
        name="Per Player",
        value=f"**{per_player:,}**" if nb_players > 0 else "—",
        inline=True,
    )

    if lootsplit.players:
        names = "\n" + "\n".join(p.albion_character_name for p in lootsplit.players)
        limit = 1024 - 6
        chunks = []
        while names:
            if len(names) <= limit:
                chunks.append(names)
                break
            split_at = names.rfind("\n", 0, limit)
            if split_at == -1:
                split_at = limit
            chunks.append(names[:split_at])
            names = names[split_at:].lstrip("\n")

        for i, chunk in enumerate(chunks):
            label = "Players" if i == 0 else "Players (cont.)"
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


def _is_admin(interaction: discord.Interaction) -> bool:
    return (
        isinstance(interaction.user, discord.Member)
        and interaction.user.guild_permissions.administrator
    )


class LootsplitView(discord.ui.View):
    def __init__(
        self,
        lootsplit_manager: ILootsplitManager,
        lootsplit: Lootsplit | None,
        database_manager: IDatabaseManager,
    ):
        super().__init__(timeout=None)
        self.lootsplit_manager = lootsplit_manager
        self.database_manager = database_manager
        self.lootsplit = lootsplit
        self._update_buttons()

    def _update_buttons(self):
        if self.lootsplit is None:
            return  # placeholder view registered at startup, no state to update
        paid_out = self.lootsplit.paid_out
        has_players = bool(self.lootsplit.players)
        self.add_players_button.disabled = paid_out
        self.edit_split_button.disabled = paid_out
        self.pay_players_button.disabled = paid_out or not has_players
        self.reopen_split_button.disabled = not paid_out

    async def _refresh_panel(self, interaction: discord.Interaction):
        if not self.lootsplit or not self.lootsplit.id:
            raise Exception("Lootsplit must have an ID here")
        self.lootsplit = await self.database_manager.get_lootsplit_by_id(
            self.lootsplit.id
        )
        self._update_buttons()
        embed = _build_lootsplit_embed(self.lootsplit)
        await interaction.message.edit(embed=embed, view=self)

    # -------------------------------------------------------------------------
    # Add Players
    # -------------------------------------------------------------------------

    @discord.ui.button(
        label="Add Players",
        style=discord.ButtonStyle.primary,
        row=0,
        custom_id="lootsplit:add_players",
    )
    async def add_players_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not _is_admin(interaction):
            await interaction.response.send_message("❌ Admins only.", ephemeral=True)
            return
        if not await self._load_lootsplit(interaction):
            return
        modal = AddPlayersModal(
            lootsplit_id=self.lootsplit.id,
            lootsplit_manager=self.lootsplit_manager,
            view=self,
        )
        await interaction.response.send_modal(modal)

    # -------------------------------------------------------------------------
    # Edit Split
    # -------------------------------------------------------------------------

    @discord.ui.button(
        label="Edit Split",
        style=discord.ButtonStyle.secondary,
        row=0,
        custom_id="lootsplit:edit_split",
    )
    async def edit_split_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not _is_admin(interaction):
            await interaction.response.send_message("❌ Admins only.", ephemeral=True)
            return
        if not await self._load_lootsplit(interaction):
            return
        modal = EditSplitModal(
            lootsplit=self.lootsplit,
            lootsplit_manager=self.lootsplit_manager,
            database_manager=self.database_manager,
            view=self,
        )
        await interaction.response.send_modal(modal)

    # -------------------------------------------------------------------------
    # Pay Players
    # -------------------------------------------------------------------------

    @discord.ui.button(
        label="Pay Players",
        style=discord.ButtonStyle.success,
        row=1,
        custom_id="lootsplit:pay_players",
    )
    async def pay_players_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not _is_admin(interaction):
            await interaction.response.send_message("❌ Admins only.", ephemeral=True)
            return
        if not await self._load_lootsplit(interaction):
            return

        await interaction.response.defer()

        try:
            await self.lootsplit_manager.add_balances(lootsplit_id=self.lootsplit.id)
        except Exception as e:
            raise e
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return

        per_player = self.lootsplit_manager.get_lootsplit_value_per_player(
            self.lootsplit
        )
        nb_players = len(self.lootsplit.players)

        await self._refresh_panel(interaction)
        await interaction.followup.send(
            f"✅ Paid out **{per_player:,}** silver to **{nb_players}** players.",
            ephemeral=True,
        )

    # -------------------------------------------------------------------------
    # Reopen Split
    # -------------------------------------------------------------------------
    @discord.ui.button(
        label="Reopen Split",
        style=discord.ButtonStyle.danger,
        row=1,
        custom_id="lootsplit:reopen_split",
    )
    async def reopen_split_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not _is_admin(interaction):
            await interaction.response.send_message("❌ Admins only.", ephemeral=True)
            return
        if not await self._load_lootsplit(interaction):
            return

        await interaction.response.defer()

        try:
            await self.lootsplit_manager.revert_balances(lootsplit_id=self.lootsplit.id)
        except Exception as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return

        await self._refresh_panel(interaction)
        await interaction.followup.send(
            "✅ Split reopened. Balances have been reversed.", ephemeral=True
        )

    async def _load_lootsplit(self, interaction: discord.Interaction) -> bool:
        """Returns False if the lootsplit could not be found, signaling the handler to abort."""
        if self.lootsplit is not None:
            return True
        # Bot restarted — rebind using the message ID
        lootsplit = await self.database_manager.get_lootsplit_by_message_id(
            str(interaction.message.id)
        )
        if lootsplit is None:
            await interaction.response.send_message(
                "❌ Could not find this lootsplit in the database.", ephemeral=True
            )
            return False
        self.lootsplit = lootsplit
        return True


# -----------------------------------------------------------------------------
# Add Players Modal
# -----------------------------------------------------------------------------


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

        names = [n.strip() for n in self.player_names.value.splitlines() if n.strip()]
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


# -----------------------------------------------------------------------------
# Edit Split Modal
# -----------------------------------------------------------------------------


class EditSplitModal(discord.ui.Modal, title="Edit Loot Split"):
    def __init__(
        self,
        lootsplit: Lootsplit,
        lootsplit_manager: ILootsplitManager,
        database_manager: IDatabaseManager,
        view: LootsplitView,
    ):
        super().__init__()
        self.lootsplit = lootsplit
        self.lootsplit_manager = lootsplit_manager
        self.database_manager = database_manager
        self.lootsplit_view = view

        # Pre-populate fields with current values
        self.item_value = discord.ui.TextInput(
            label="Item Value",
            default=str(lootsplit.item_value),
            required=True,
        )
        self.silver = discord.ui.TextInput(
            label="Silver",
            default=str(lootsplit.silver),
            required=True,
        )
        self.repair_cost = discord.ui.TextInput(
            label="Repair Cost",
            default=str(lootsplit.repair_cost),
            required=True,
        )
        self.player_names = discord.ui.TextInput(
            label="Players (one per line, replaces current list)",
            style=discord.TextStyle.paragraph,
            default="\n".join(p.albion_character_name for p in lootsplit.players),
            required=False,
        )

        self.add_item(self.item_value)
        self.add_item(self.silver)
        self.add_item(self.repair_cost)
        self.add_item(self.player_names)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Validate numeric fields
        try:
            new_item_value = int(self.item_value.value.strip().replace(",", ""))
            new_silver = int(self.silver.value.strip().replace(",", ""))
            new_repair_cost = int(self.repair_cost.value.strip().replace(",", ""))
        except ValueError:
            await interaction.followup.send(
                "❌ Item Value, Silver, and Repair Cost must all be integers.",
                ephemeral=True,
            )
            return

        self.lootsplit.item_value = new_item_value
        self.lootsplit.silver = new_silver
        self.lootsplit.repair_cost = new_repair_cost

        # Update player list if provided
        names = [n.strip() for n in self.player_names.value.splitlines() if n.strip()]
        if names:
            self.lootsplit.players = []
            await self.database_manager.save_or_update_lootsplit(self.lootsplit)
            await self.lootsplit_manager.add_players_by_name(
                character_names=names,
                lootsplit_id=self.lootsplit.id,
            )
        else:
            await self.database_manager.save_or_update_lootsplit(self.lootsplit)

        await self.lootsplit_view._refresh_panel(interaction)
        await interaction.followup.send("✅ Loot split updated.", ephemeral=True)
