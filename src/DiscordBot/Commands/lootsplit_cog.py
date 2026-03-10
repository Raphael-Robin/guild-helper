import random
from datetime import datetime, timedelta, timezone
from typing import Optional
import discord
from discord import TextChannel, app_commands
from discord.ext import commands
from src.Interfaces import ILootsplitManager, IDatabaseManager, IConfigurationManager
from src.Model import Lootsplit, SplitSale, Auction, AuctionBid, SplitMode

from src.DiscordBot.permissions import is_admin, is_lootsplit_manager, send_permission_error
from src.utils.logger import logger

PAGE_SIZE = 10
MIN_INCREMENT = 50000


# -----------------------------------------------------------------------------
# Cog
# -----------------------------------------------------------------------------

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
            raise Exception("Interaction needs a guild here")

        lootsplit = await self.lootsplit_manager.create_lootsplit(
            item_value=item_value,
            silver=silver,
            repair_cost=repair_cost,
            guild_discord_id=str(interaction.guild.id),
        )

        embed = await self.lootsplit_manager._build_lootsplit_embed(lootsplit, auction=None)
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

    @app_commands.command(
        name="my-splits",
        description="List all loot splits you are part of.",
    )
    @app_commands.describe(user="The user to check splits for (admin only, defaults to yourself)")
    async def my_splits(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ):
        logger.info(f"{interaction.user.name} used /my-splits")
        await interaction.response.defer(ephemeral=True)

        if user is not None and user.id != interaction.user.id:
            if not await is_admin(interaction, self.configuration_manager):
                await send_permission_error(interaction)
                return

        target = user or interaction.user
        lootsplits = await self.database_manager.get_lootsplits_for_player(str(target.id))

        if not lootsplits:
            await interaction.followup.send(
                f"❌ No loot splits found for {target.mention}.", ephemeral=True
            )
            return

        if not isinstance(target, discord.Member):
            raise Exception("Target must be a guild member")

        embed = await self.lootsplit_manager._build_splits_list_embed(lootsplits, target, page=0)
        view = (
            SplitsListView(lootsplit_manager=self.lootsplit_manager,lootsplits=lootsplits, target=target)
            if len(lootsplits) > PAGE_SIZE
            else discord.utils.MISSING
        )

        await interaction.followup.send(
            embed=embed,
            view=view if view is not discord.utils.MISSING else discord.utils.MISSING,
            ephemeral=True,
        )




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
        mode = getattr(self.lootsplit.configuration, "split_mode", None)

        self.add_players_button.disabled = paid_out
        self.edit_split_button.disabled = paid_out
        self.reopen_split_button.disabled = not paid_out
        self.delete_button.disabled = paid_out
        self.pay_players_button.disabled = paid_out or not has_players
        self.sell_split_button.disabled = paid_out or mode != SplitMode.sale
        self.auction_button.disabled = paid_out or mode != SplitMode.auction

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

        self.lootsplit = await self.database_manager.get_lootsplit_by_id(self.lootsplit.id)
        auction = await self.database_manager.get_auction_by_lootsplit_id(self.lootsplit.id)
        self._update_buttons()
        embed = await self.lootsplit_manager._build_lootsplit_embed(self.lootsplit, auction=auction)

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
            raise Exception("No lootsplit found")

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
            raise Exception("Missing lootsplit, id, or guild")

        sale = await self.lootsplit_manager.create_split_sale(
            lootsplit_id=self.lootsplit.id, guild_discord_id=str(interaction.guild.id)
        )
        sale_embed = self.lootsplit_manager._build_sale_embed(sale=sale, lootsplit=self.lootsplit)
        sale_view = SplitSaleView(
            lootsplit_manager=self.lootsplit_manager,
            database_manager=self.database_manager,
            configuration_manager=self.configuration_manager,
            sale=sale,
            lootsplit=self.lootsplit,
        )

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
    # Auction
    # -------------------------------------------------------------------------

    @discord.ui.button(
        label="🔨 Auction",
        style=discord.ButtonStyle.primary,
        row=0,
        custom_id="lootsplit:auction",
    )
    async def auction_button(
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
            and interaction.channel
            and interaction.message
            and interaction.guild
        ):
            raise Exception("Missing lootsplit, id, or channel")

        min_bid = self.lootsplit_manager._compute_auction_min_bid(self.lootsplit)
        
        config = await self.configuration_manager.get_config(str(interaction.guild.id))

        deadline = datetime.now(timezone.utc) + timedelta(
            minutes=config.lootsplit_sale_timer_minutes
        )
        auction = Auction(
            lootsplit_id=self.lootsplit.id,
            deadline=deadline.replace(tzinfo=None),
            min_bid=min_bid,
        )
        await self.database_manager.save_or_update_auction(auction)

        embed = self.lootsplit_manager._build_auction_embed(auction, self.lootsplit)
        auction_view = AuctionView(
            database_manager=self.database_manager,
            lootsplit_manager=self.lootsplit_manager,
            auction=auction,
            lootsplit=self.lootsplit,
            configuration_manager=self.configuration_manager,
        )

        message = await interaction.channel.send(embed=embed, view=auction_view)
        auction.discord_message_id = str(message.id)
        auction_view.auction = auction
        await self.database_manager.save_or_update_auction(auction)

        self.auction_button.disabled = True
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

        if not (self.lootsplit and self.lootsplit.id):
            raise Exception("No lootsplit found")

        try:
            await self.lootsplit_manager.add_balances(lootsplit_id=self.lootsplit.id)
        except Exception as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return

        per_player = await self.lootsplit_manager.get_lootsplit_value_per_player(self.lootsplit)
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

        if not (self.lootsplit and self.lootsplit.id):
            raise Exception("Lootsplit must have an ID here")

        try:
            await self.lootsplit_manager.revert_balances(lootsplit_id=self.lootsplit.id)
        except Exception as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return

        await self._refresh_panel(interaction)
        await interaction.followup.send(
            "✅ Split reopened. Balances have been reversed.", ephemeral=True
        )

    # -------------------------------------------------------------------------
    # Delete Split
    # -------------------------------------------------------------------------

    @discord.ui.button(
        label="🗑️ Delete",
        style=discord.ButtonStyle.danger,
        row=2,
        custom_id="lootsplit:delete",
    )
    async def delete_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not await is_admin(interaction, self.configuration_manager):
            await send_permission_error(interaction)
            return
        if not await self._load_lootsplit(interaction):
            return

        if not (self.lootsplit and self.lootsplit.id) or not interaction.message:
            raise Exception("Missing lootsplit or message")

        await interaction.response.defer()
        await self.database_manager.delete_lootsplit(self.lootsplit.id)
        await interaction.message.delete()
        await interaction.followup.send(
            f"✅ Loot split #{self.lootsplit.id} has been deleted.", ephemeral=True
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
        if not interaction.message:
            raise Exception("No message found")

        split_sale = await self.database_manager.get_split_sale_by_message_id(
            str(interaction.message.id)
        )
        if split_sale is None:
            await interaction.response.send_message(
                "❌ Could not find this auction in the database.", ephemeral=True
            )
            return False
        self.sale = split_sale
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
        embed = self.lootsplit_manager._build_sale_embed(sale=self.sale, lootsplit=self.lootsplit)
        await interaction.message.edit(embed=embed, view=self)

    async def _end_sale(self, interaction: discord.Interaction):
        if not self.sale or not self.lootsplit:
            raise Exception("Sale or Lootsplit is None")

        if self.sale.participants:
            self.sale.winner_id = random.choice(self.sale.participants)
        self.sale.ended = True
        await self.database_manager.save_or_update_split_sale(self.sale)
        await self._refresh_sale_panel(interaction)

        _, _, _, total_payout = await self.lootsplit_manager._compute_lootsplit_payout(self.lootsplit)

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
        embed = self.lootsplit_manager._build_sale_embed(sale=self.sale, lootsplit=self.lootsplit)
        await message.edit(embed=embed, view=self)

        _, _, _, total_payout = await self.lootsplit_manager._compute_lootsplit_payout(self.lootsplit)

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

        if not self.sale:
            raise Exception("No sale found")

        user_id = str(interaction.user.id)
        if user_id in self.sale.participants:
            await interaction.response.send_message(
                "❌ You have already joined this sale.", ephemeral=True
            )
            return

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
# AuctionView
# -----------------------------------------------------------------------------


class AuctionView(discord.ui.View):
    def __init__(
        self,
        database_manager: IDatabaseManager,
        lootsplit_manager: ILootsplitManager,
        auction: Auction | None,
        lootsplit: Lootsplit | None,
        configuration_manager: IConfigurationManager,
    ):
        super().__init__(timeout=None)
        self.database_manager = database_manager
        self.lootsplit_manager = lootsplit_manager
        self.auction = auction
        self.lootsplit = lootsplit
        self.configuration_manager = configuration_manager
        self._update_buttons()

    def _update_buttons(self):
        if self.auction is None:
            return
        self.bid_button.disabled = self.auction.ended
        self.force_end_button.disabled = self.auction.ended

    async def _load_state(self, interaction: discord.Interaction) -> bool:
        if not interaction.message:
            raise Exception("No message found")

        auction = await self.database_manager.get_auction_by_message_id(
            str(interaction.message.id)
        )
        if auction is None:
            await interaction.response.send_message(
                "❌ Could not find this auction in the database.", ephemeral=True
            )
            return False
        self.auction = auction
        self.lootsplit = await self.database_manager.get_lootsplit_by_id(
            self.auction.lootsplit_id
        )
        return True
        return True

    async def _refresh_panel(self, interaction: discord.Interaction):
        if not interaction.message:
            raise Exception("No message found")

        self.auction = await self.database_manager.get_auction_by_message_id(
            str(interaction.message.id)
        )
        if not self.auction:
            raise Exception("No auction found")

        self.lootsplit = await self.database_manager.get_lootsplit_by_id(
            self.auction.lootsplit_id
        )
        self._update_buttons()
        embed = self.lootsplit_manager._build_auction_embed(self.auction, self.lootsplit)
        await interaction.message.edit(embed=embed, view=self)

    async def _update_lootsplit_panel(self, channel: discord.abc.Messageable):
        """Fetch and refresh the lootsplit panel after auction ends."""
        if not self.lootsplit or not self.lootsplit.discord_message_id:
            return
        try:
            ls_message = await channel.fetch_message(int(self.lootsplit.discord_message_id))
        except discord.NotFound:
            return
        if not self.lootsplit.id:
            raise Exception()
        auction = await self.database_manager.get_auction_by_lootsplit_id(self.lootsplit.id)
        embed = await self.lootsplit_manager._build_lootsplit_embed(self.lootsplit, auction=auction)
        await ls_message.edit(embed=embed)


    async def _end_auction(self, interaction: discord.Interaction):
        if not self.auction or not self.lootsplit:
            raise Exception("Auction or lootsplit is None")

        if self.auction.bids:
            winning_bid = max(self.auction.bids, key=lambda b: b.amount)
            self.auction.winner_id = winning_bid.discord_user_id
            self.auction.winning_bid = winning_bid.amount
        self.auction.ended = True
        await self.database_manager.save_or_update_auction(self.auction)
        await self._refresh_panel(interaction)

        # Update the lootsplit panel
        if interaction.channel and isinstance(interaction.channel, TextChannel):
            await self._update_lootsplit_panel(interaction.channel)

        if self.auction.winner_id:
            await interaction.followup.send(
                f"🎉 <@{self.auction.winner_id}> won the auction with a bid of "
                f"**{self.auction.winning_bid:,}** silver! Please arrange payment."
            )
        else:
            await interaction.followup.send("❌ Auction ended with no bids.")


    async def _end_auction_from_task(self, message: discord.Message):
        if not (self.auction and self.lootsplit):
            raise Exception("Auction or lootsplit is none")

        if self.auction.bids:
            winning_bid = max(self.auction.bids, key=lambda b: b.amount)
            self.auction.winner_id = winning_bid.discord_user_id
            self.auction.winning_bid = winning_bid.amount
        self.auction.ended = True
        await self.database_manager.save_or_update_auction(self.auction)

        self._update_buttons()
        embed = self.lootsplit_manager._build_auction_embed(self.auction, self.lootsplit)
        await message.edit(embed=embed, view=self)

        # Update the lootsplit panel
        await self._update_lootsplit_panel(message.channel)

        if self.auction.winner_id:
            await message.channel.send(
                f"🎉 <@{self.auction.winner_id}> won the auction with a bid of "
                f"**{self.auction.winning_bid:,}** silver! Please arrange payment."
            )
        else:
            await message.channel.send("❌ Auction ended with no bids.")

    # -------------------------------------------------------------------------
    # Place Bid
    # -------------------------------------------------------------------------

    @discord.ui.button(
        label="Place Bid",
        style=discord.ButtonStyle.success,
        row=0,
        custom_id="auction:bid",
    )
    async def bid_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not await self._load_state(interaction):
            return

        if not self.auction:
            raise Exception("No auction found")

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if now >= self.auction.deadline:
            await interaction.response.defer()
            await self._end_auction(interaction)
            return

        if not self.lootsplit:
            raise Exception("No lootsplit found")

        modal = PlaceBidModal(
            auction=self.auction,
            lootsplit=self.lootsplit,
            database_manager=self.database_manager,
            view=self,
        )
        await interaction.response.send_modal(modal)

    # -------------------------------------------------------------------------
    # Force End
    # -------------------------------------------------------------------------

    @discord.ui.button(
        label="Force End",
        style=discord.ButtonStyle.danger,
        row=0,
        custom_id="auction:force_end",
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
        await self._end_auction(interaction)


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


# -----------------------------------------------------------------------------
# Place Bid Modal
# -----------------------------------------------------------------------------


class PlaceBidModal(discord.ui.Modal, title="Place Your Bid"):
    bid_amount = discord.ui.TextInput(
        label="Your Bid (silver)",
        placeholder="Enter your bid amount",
        required=True,
    )

    def __init__(
        self,
        auction: Auction,
        lootsplit: Lootsplit,
        database_manager: IDatabaseManager,
        view: AuctionView,
    ):
        super().__init__()
        self.auction = auction
        self.lootsplit = lootsplit
        self.database_manager = database_manager
        self.auction_view = view

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        fresh_auction = await self.database_manager.get_auction_by_message_id(
            str(self.auction.discord_message_id)
        )
        if not fresh_auction:
            await interaction.followup.send("❌ Auction no longer exists.", ephemeral=True)
            return
        self.auction = fresh_auction

        try:
            amount = int(self.bid_amount.value.strip().replace(",", ""))
        except ValueError:
            await interaction.followup.send(
                "❌ Please enter a valid integer.", ephemeral=True
            )
            return
        
        
        if amount < self.auction.min_bid + MIN_INCREMENT:
            await interaction.followup.send(
                f"❌ Your bid must be at least **{self.auction.min_bid+MIN_INCREMENT:,}** silver",
                ephemeral=True,
            )
            return

        user_id = str(interaction.user.id)
        
        self.auction.bids.append(AuctionBid(discord_user_id=user_id, amount=amount))
        self.auction.min_bid = amount

        await self.database_manager.save_or_update_auction(self.auction)
        await self.auction_view._refresh_panel(interaction)

        await interaction.followup.send(
            f"✅ Your bid of **{amount:,}** silver has been recorded. Good luck!",
            ephemeral=True,
        )


# -----------------------------------------------------------------------------
# Splits List View
# -----------------------------------------------------------------------------


class SplitsListView(discord.ui.View):
    def __init__(self, lootsplit_manager: ILootsplitManager, lootsplits: list[Lootsplit], target: discord.Member):
        super().__init__(timeout=120)
        self.lootsplits = lootsplits
        self.lootsplit_manager = lootsplit_manager
        self.target = target
        self.page = 0
        self._update_buttons()

    def _update_buttons(self):
        total_pages = (len(self.lootsplits) + PAGE_SIZE - 1) // PAGE_SIZE
        self.prev_button.disabled = self.page == 0
        self.next_button.disabled = self.page >= total_pages - 1

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.page -= 1
        self._update_buttons()
        embed = await self.lootsplit_manager._build_splits_list_embed(self.lootsplits, self.target, self.page)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.page += 1
        self._update_buttons()
        embed = await self.lootsplit_manager._build_splits_list_embed(self.lootsplits, self.target, self.page)
        await interaction.response.edit_message(embed=embed, view=self)