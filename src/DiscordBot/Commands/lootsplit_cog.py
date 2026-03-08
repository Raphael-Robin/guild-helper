import random
from datetime import datetime, timezone
import discord
from discord import TextChannel, app_commands
from discord.ext import commands
from src.Interfaces import ILootsplitManager, IDatabaseManager, IConfigurationManager
from src.Model import Lootsplit, SplitSale
from src.DiscordBot.permissions import is_lootsplit_manager, send_permission_error


class LootsplitCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        lootsplit_manager: ILootsplitManager,
        database_manager: IDatabaseManager,
        configuration_manager: IConfigurationManager,
    ):
        self.bot = bot
        self.lootsplit_manager = lootsplit_manager
        self.database_manager = database_manager
        self.configuration_manager = configuration_manager

    @app_commands.command(
        name="lootsplit", description="[Admin] Create a new loot split."
    )
    @app_commands.describe(
        item_value="Total value of items sold",
        silver="Silver collected",
        repair_cost="Total repair cost to deduct",
    )
    async def lootsplit(
        self,
        interaction: discord.Interaction,
        item_value: int,
        silver: int,
        repair_cost: int,
    ):

        if not await is_lootsplit_manager(
            interaction=interaction, configuration_manager=self.configuration_manager
        ):
            await send_permission_error(interaction=interaction)
            return

        await interaction.response.defer()

        if not interaction.guild:
            raise Exception("Interation needs a guild here")

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
            configuration_manager=self.configuration_manager,
        )
        message = await interaction.followup.send(embed=embed, view=view, wait=True)
        lootsplit.discord_message_id = str(message.id)
        lootsplit.discord_channel_id = str(interaction.channel_id)
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


# -----------------------------------------------------------------------------
# Embed builders
# -----------------------------------------------------------------------------


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


def _build_sale_embed(sale: SplitSale, lootsplit: Lootsplit) -> discord.Embed:
    config = lootsplit.configuration
    gross = lootsplit.item_value + lootsplit.silver
    after_repairs = gross - lootsplit.repair_cost
    sale_tax_amount = round(after_repairs * (config.lootsplit_sale_tax_percent / 100))
    guild_tax_amount = round(after_repairs * (config.guild_tax_percent / 100))
    total_payout = after_repairs - sale_tax_amount - guild_tax_amount

    if sale.ended and sale.winner_id:
        color = discord.Color.green()
        title = f"Split Sale #{lootsplit.id} — Sold!"
    elif sale.ended:
        color = discord.Color.red()
        title = f"Split Sale #{lootsplit.id} — Ended (No Participants)"
    else:
        color = discord.Color.blurple()
        title = f"Split Sale #{lootsplit.id} — Open"

    embed = discord.Embed(title=title, color=color)

    embed.add_field(name="Split Value", value=f"**{total_payout:,}**", inline=True)

    if not sale.ended:
        deadline_ts = int(sale.deadline.replace(tzinfo=timezone.utc).timestamp())
        embed.add_field(name="Closing", value=f"<t:{deadline_ts}:R>", inline=False)

    if sale.participants:
        mentions = "\n".join(f"<@{uid}>" for uid in sale.participants)
        embed.add_field(
            name=f"Participants ({len(sale.participants)})",
            value=mentions,
            inline=False,
        )
    else:
        embed.add_field(
            name="Participants",
            value="None yet — click Join to enter!",
            inline=False,
        )

    if sale.ended and sale.winner_id:
        embed.add_field(
            name="Winner",
            value=f"<@{sale.winner_id}> — please arrange payment of **{total_payout:,}** silver.",
            inline=False,
        )

    return embed


# -----------------------------------------------------------------------------
# LootsplitView
# -----------------------------------------------------------------------------


class LootsplitView(discord.ui.View):
    def __init__(
        self,
        lootsplit_manager: ILootsplitManager,
        lootsplit: Lootsplit | None,
        database_manager: IDatabaseManager,
        configuration_manager: IConfigurationManager,
    ):
        super().__init__(timeout=None)
        self.lootsplit_manager = lootsplit_manager
        self.database_manager = database_manager
        self.configuration_manager = configuration_manager
        self.lootsplit = lootsplit
        self._update_buttons()

    def _update_buttons(self):
        if self.lootsplit is None:
            return
        paid_out = self.lootsplit.paid_out
        has_players = bool(self.lootsplit.players)
        guild_buys = self.lootsplit.configuration.guild_buys_split

        self.add_players_button.disabled = paid_out
        self.edit_split_button.disabled = paid_out
        self.reopen_split_button.disabled = not paid_out
        self.pay_players_button.disabled = paid_out or not has_players
        self.sell_split_button.disabled = paid_out or guild_buys

    async def _load_lootsplit(self, interaction: discord.Interaction) -> bool:
        if self.lootsplit is not None:
            return True

        if not interaction.message:
            raise Exception("No message found")
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

    async def _refresh_panel(self, interaction: discord.Interaction):
        if not self.lootsplit or not self.lootsplit.id:
            raise Exception("Lootsplit must have an ID here")
        self.lootsplit = await self.database_manager.get_lootsplit_by_id(
            self.lootsplit.id
        )
        self._update_buttons()
        embed = _build_lootsplit_embed(self.lootsplit)
        if not interaction.message:
            raise Exception("No message found")
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

        if not await is_lootsplit_manager(
            interaction=interaction, configuration_manager=self.configuration_manager
        ):
            await send_permission_error(interaction=interaction)
            return
        if not await self._load_lootsplit(interaction):
            return

        if not (self.lootsplit and self.lootsplit.id):
            raise Exception("No lootsplit found")
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

        if not await is_lootsplit_manager(
            interaction=interaction, configuration_manager=self.configuration_manager
        ):
            await send_permission_error(interaction=interaction)
            return
        if not await self._load_lootsplit(interaction):
            return

        if not self.lootsplit:
            raise Exception("No message found")
        modal = EditSplitModal(
            lootsplit=self.lootsplit,
            lootsplit_manager=self.lootsplit_manager,
            database_manager=self.database_manager,
            view=self,
        )
        await interaction.response.send_modal(modal)

    # -------------------------------------------------------------------------
    # Sell Split
    # -------------------------------------------------------------------------

    @discord.ui.button(
        label="Sell Split",
        style=discord.ButtonStyle.primary,
        row=0,
        custom_id="lootsplit:sell_split",
    )
    async def sell_split_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        if not await is_lootsplit_manager(
            interaction=interaction, configuration_manager=self.configuration_manager
        ):
            await send_permission_error(interaction=interaction)
            return
        if not await self._load_lootsplit(interaction):
            return

        await interaction.response.defer()

        if not (
            self.lootsplit
            and self.lootsplit.id
            and interaction.guild
            and interaction.guild.id
        ):
            raise Exception()
        sale = await self.lootsplit_manager.create_split_sale(
            lootsplit_id=self.lootsplit.id, guild_discord_id=str(interaction.guild.id)
        )
        sale_embed = _build_sale_embed(sale=sale, lootsplit=self.lootsplit)
        sale_view = SplitSaleView(
            lootsplit_manager=self.lootsplit_manager,
            database_manager=self.database_manager,
            configuration_manager=self.configuration_manager,
            sale=sale,
            lootsplit=self.lootsplit,
        )

        # Mention buyer role if configured
        buyer_role_id = self.lootsplit.configuration.lootsplit_buyer_role_id
        content = f"<@&{buyer_role_id}>" if buyer_role_id else None

        if not (
            interaction.message
            and interaction.channel
            and isinstance(interaction.channel, TextChannel)
        ):
            raise Exception("No channel found")
        message = await interaction.channel.send(
            content=content, embed=sale_embed, view=sale_view
        )
        sale.discord_message_id = str(message.id)
        sale_view.sale = sale
        await self.database_manager.save_or_update_split_sale(sale)

        self.sell_split_button.disabled = True
        await interaction.message.edit(view=self)

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

        if not await is_lootsplit_manager(
            interaction=interaction, configuration_manager=self.configuration_manager
        ):
            await send_permission_error(interaction=interaction)
            return
        if not await self._load_lootsplit(interaction):
            return

        await interaction.response.defer()

        try:
            if not (self.lootsplit and self.lootsplit.id):
                raise Exception("No message found")
            await self.lootsplit_manager.add_balances(lootsplit_id=self.lootsplit.id)
        except Exception as e:
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

        if not await is_lootsplit_manager(
            interaction=interaction, configuration_manager=self.configuration_manager
        ):
            await send_permission_error(interaction=interaction)
            return
        if not await self._load_lootsplit(interaction):
            return

        await interaction.response.defer()

        try:
            if not self.lootsplit or not self.lootsplit.id:
                raise Exception("Lootsplit must have an ID here")
            await self.lootsplit_manager.revert_balances(lootsplit_id=self.lootsplit.id)
        except Exception as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return

        await self._refresh_panel(interaction)
        await interaction.followup.send(
            "✅ Split reopened. Balances have been reversed.", ephemeral=True
        )


# -----------------------------------------------------------------------------
# SplitSaleView
# -----------------------------------------------------------------------------


class SplitSaleView(discord.ui.View):
    def __init__(
        self,
        lootsplit_manager: ILootsplitManager,
        database_manager: IDatabaseManager,
        configuration_manager: IConfigurationManager,
        sale: SplitSale | None,
        lootsplit: Lootsplit | None,
    ):
        super().__init__(timeout=None)
        self.lootsplit_manager = lootsplit_manager
        self.database_manager = database_manager
        self.configuration_manager = configuration_manager
        self.sale = sale
        self.lootsplit = lootsplit
        self._update_buttons()

    def _update_buttons(self):
        if self.sale is None:
            return
        self.join_button.disabled = self.sale.ended
        self.force_end_button.disabled = self.sale.ended

    async def _load_state(self, interaction: discord.Interaction) -> bool:
        if self.sale is None:
            if not interaction.message:
                raise Exception("No message found")
            sale = await self.database_manager.get_split_sale_by_message_id(
                str(interaction.message.id)
            )
            if sale is None:
                await interaction.response.send_message(
                    "❌ Could not find this sale in the database.", ephemeral=True
                )
                return False
            self.sale = sale

        if self.lootsplit is None:
            self.lootsplit = await self.database_manager.get_lootsplit_by_id(
                self.sale.lootsplit_id
            )

        return True

    async def _refresh_sale_panel(self, interaction: discord.Interaction):

        if not interaction.message:
            raise Exception("No message found")
        self.sale = await self.database_manager.get_split_sale_by_message_id(
            str(interaction.message.id)
        )
        if not self.sale:
            raise Exception("No sale found")
        self.lootsplit = await self.database_manager.get_lootsplit_by_id(
            self.sale.lootsplit_id
        )
        self._update_buttons()
        embed = _build_sale_embed(sale=self.sale, lootsplit=self.lootsplit)
        await interaction.message.edit(embed=embed, view=self)

    async def _end_sale(self, interaction: discord.Interaction):
        if not self.sale or not self.lootsplit:
            raise Exception("Sale or Lootsplit is None")
        if self.sale.participants:
            self.sale.winner_id = random.choice(self.sale.participants)
        self.sale.ended = True
        await self.database_manager.save_or_update_split_sale(self.sale)
        await self._refresh_sale_panel(interaction)

        config = self.lootsplit.configuration
        gross = self.lootsplit.item_value + self.lootsplit.silver
        after_repairs = gross - self.lootsplit.repair_cost
        sale_tax = round(after_repairs * (config.lootsplit_sale_tax_percent / 100))
        guild_tax = round(after_repairs * (config.guild_tax_percent / 100))
        total_payout = after_repairs - sale_tax - guild_tax

        if self.sale.winner_id:
            await interaction.followup.send(
                f"🎉 <@{self.sale.winner_id}> has been selected as the buyer! "
                f"Please arrange payment of **{total_payout:,}** silver."
            )
        else:
            await interaction.followup.send(
                "❌ Sale ended with no participants — no buyer selected."
            )

    async def _end_sale_from_task(self, message: discord.Message):
        if not (self.sale and self.lootsplit):
            raise Exception("Sale or lootsplit is none")
        if self.sale.participants:
            self.sale.winner_id = random.choice(self.sale.participants)
        self.sale.ended = True
        await self.database_manager.save_or_update_split_sale(self.sale)

        self._update_buttons()
        embed = _build_sale_embed(sale=self.sale, lootsplit=self.lootsplit)
        await message.edit(embed=embed, view=self)

        config = self.lootsplit.configuration
        gross = self.lootsplit.item_value + self.lootsplit.silver
        after_repairs = gross - self.lootsplit.repair_cost
        sale_tax = round(after_repairs * (config.lootsplit_sale_tax_percent / 100))
        guild_tax = round(after_repairs * (config.guild_tax_percent / 100))
        total_payout = after_repairs - sale_tax - guild_tax

        if self.sale.winner_id:
            await message.channel.send(
                f"🎉 <@{self.sale.winner_id}> has been selected as the buyer! "
                f"Please arrange payment of **{total_payout:,}** silver."
            )
        else:
            await message.channel.send(
                "❌ Sale timer expired with no participants — no buyer selected."
            )

    # -------------------------------------------------------------------------
    # Join Sale
    # -------------------------------------------------------------------------

    @discord.ui.button(
        label="Join Sale",
        style=discord.ButtonStyle.success,
        row=0,
        custom_id="splitsale:join",
    )
    async def join_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not await self._load_state(interaction):
            return

        # Check buyer role
        if not self.lootsplit:
            raise Exception("No lootsplit found")
        config = self.lootsplit.configuration
        if config.lootsplit_buyer_role_id:
            buyer_role_id = int(config.lootsplit_buyer_role_id)
            if not isinstance(interaction.user, discord.Member) or not any(
                r.id == buyer_role_id for r in interaction.user.roles
            ):
                await interaction.response.send_message(
                    "❌ You need the buyer role to join this sale.", ephemeral=True
                )
                return

        user_id = str(interaction.user.id)
        if not self.sale:
            raise Exception("No sale found")
        if user_id in self.sale.participants:
            await interaction.response.send_message(
                "❌ You have already joined this sale.", ephemeral=True
            )
            return

        # Check if timer expired
        deadline = self.sale.deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) >= deadline:
            await interaction.response.defer()
            await self._end_sale(interaction)
            return

        self.sale.participants.append(user_id)
        await self.database_manager.save_or_update_split_sale(self.sale)

        await interaction.response.defer()
        await self._refresh_sale_panel(interaction)

    # -------------------------------------------------------------------------
    # Force End
    # -------------------------------------------------------------------------

    @discord.ui.button(
        label="Force End",
        style=discord.ButtonStyle.danger,
        row=0,
        custom_id="splitsale:force_end",
    )
    async def force_end_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        if not await is_lootsplit_manager(
            interaction=interaction, configuration_manager=self.configuration_manager
        ):
            await send_permission_error(interaction=interaction)
            return
        if not await self._load_state(interaction):
            return

        await interaction.response.defer()
        await self._end_sale(interaction)


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

        if not self.lootsplit.guild_discord_id:
            raise Exception("Lootsplit needs a guild discord id here")
        self.lootsplit.configuration = await self.database_manager.get_configuration(
            self.lootsplit.guild_discord_id
        )

        names = [n.strip() for n in self.player_names.value.splitlines() if n.strip()]
        if names:
            self.lootsplit.players = []
            await self.database_manager.save_or_update_lootsplit(self.lootsplit)
            if not self.lootsplit.id:
                raise Exception("Lootsplit needs an id here")
            await self.lootsplit_manager.add_players_by_name(
                character_names=names,
                lootsplit_id=self.lootsplit.id,
            )
        else:
            await self.database_manager.save_or_update_lootsplit(self.lootsplit)

        await self.lootsplit_view._refresh_panel(interaction)
        await interaction.followup.send("✅ Loot split updated.", ephemeral=True)
