from datetime import datetime, timedelta, timezone
from typing import Optional

import discord

from src.Interfaces import (
    ILootsplitManager,
    IConfigurationManager,
    IDatabaseManager,
    IEconomyManager,
)
from src.Model import Player, Lootsplit, SplitSale, SplitMode, Auction


class LootsplitManager(ILootsplitManager):
    def __init__(
        self,
        configuration_manager: IConfigurationManager,
        database_manager: IDatabaseManager,
        economy_manager: IEconomyManager,
    ) -> None:
        self.configuration_manager = configuration_manager
        self.database_manager = database_manager
        self.economy_manager = economy_manager

    async def create_lootsplit(
        self, item_value: int, silver: int, repair_cost: int, guild_discord_id: str
    ) -> Lootsplit:
        config = await self.configuration_manager.get_config(guild_discord_id)
        return Lootsplit(
            configuration=config,
            players=[],
            item_value=item_value,
            silver=silver,
            repair_cost=repair_cost,
            guild_discord_id=guild_discord_id,
        )

    async def add_players_by_name(
        self, character_names: list[str], lootsplit_id: int
    ) -> None:
        players = await self.database_manager.get_or_create_players_from_characters(
            character_names=character_names
        )
        lootsplit = await self.database_manager.get_lootsplit_by_id(
            lootsplit_id=lootsplit_id
        )
        if not lootsplit.guild_discord_id:
            raise Exception("Lootsplits Guild discord id should not be none here")
        lootsplit.configuration = await self.configuration_manager.get_config(
            guild_discord_server_id=lootsplit.guild_discord_id
        )
        lootsplit.players.extend(
            [player for player in players if player not in lootsplit.players]
        )
        await self.database_manager.save_or_update_lootsplit(lootsplit=lootsplit)

    async def add_players(self, players: list[Player], lootsplit_id: int) -> None:
        lootsplit = await self.database_manager.get_lootsplit_by_id(
            lootsplit_id=lootsplit_id
        )
        if not lootsplit.guild_discord_id:
            raise Exception("Lootsplits Guild discord id should not be none here")
        lootsplit.configuration = await self.configuration_manager.get_config(
            guild_discord_server_id=lootsplit.guild_discord_id
        )
        lootsplit.players.extend(
            [player for player in players if player not in lootsplit.players]
        )
        await self.database_manager.save_or_update_lootsplit(lootsplit=lootsplit)

    async def add_balances(self, lootsplit_id: int) -> None:
        lootsplit = await self.database_manager.get_lootsplit_by_id(
            lootsplit_id=lootsplit_id
        )
        if lootsplit.paid_out:
            raise Exception("Lootsplit already paid out")
        amount = await self.get_lootsplit_value_per_player(lootsplit=lootsplit)
        albion_character_ids = [
            player.albion_character_id for player in lootsplit.players
        ]
        await self.economy_manager.add_balances(
            albion_character_ids=albion_character_ids, amount=amount
        )
        lootsplit.paid_out = True
        await self.database_manager.save_or_update_lootsplit(lootsplit=lootsplit)

    def get_lootsplit_value_total(self, lootsplit: Lootsplit) -> int:
        return round(
            (lootsplit.item_value + lootsplit.silver - lootsplit.repair_cost)
            * (1 - lootsplit.configuration.guild_tax_percent / 100)
        )

    async def get_lootsplit_value_per_player(self, lootsplit: Lootsplit) -> int:
        value_after_repairs, sale_tax_amount, guild_tax_amount, total_payout = await self._compute_lootsplit_payout(lootsplit=lootsplit)
        return round(total_payout / len(lootsplit.players))
    
    async def _compute_lootsplit_payout(self, lootsplit: Lootsplit) -> tuple[int, int, int, int]:
        """Returns (value_after_repairs, sale_tax_amount, guild_tax_amount, total_payout).

        Split sale formula:
        1. item_value - repair_cost                       = value_after_repairs
        2. value_after_repairs * (1 - sale_tax%)          = sale_proceeds
        3. sale_proceeds + silver                         = pre_guild_tax
        4. pre_guild_tax * (1 - guild_tax%)               = total_payout

        Auction: total_payout is 0 until winning bid is known (use _compute_auction_payout).
        """
        config = lootsplit.configuration
        value_after_repairs = lootsplit.item_value - lootsplit.repair_cost

        if self._is_auction_mode(lootsplit):
            auction = await self.database_manager.get_auction_by_lootsplit_id(lootsplit_id=lootsplit.id)
            if not auction:
                sale_tax_amount = 0
                guild_tax_amount = 0
                total_payout = 0
            else:
                if auction.ended and auction.winning_bid:
                    sale_tax_amount = 0
                    total_payout = auction.winning_bid
                    guild_tax_amount = round(total_payout * (config.guild_tax_percent / 100))
                else:
                    sale_tax_amount = 0
                    guild_tax_amount = 0
                    total_payout = 0

        else:
            sale_tax_amount = round(value_after_repairs * (config.lootsplit_sale_tax_percent / 100))
            sale_proceeds = value_after_repairs - sale_tax_amount
            pre_guild_tax = sale_proceeds + lootsplit.silver
            guild_tax_amount = round(pre_guild_tax * (config.guild_tax_percent / 100))
            total_payout = pre_guild_tax - guild_tax_amount

        return value_after_repairs, sale_tax_amount, guild_tax_amount, total_payout
    
    def _is_auction_mode(self, lootsplit: Lootsplit) -> bool:
        config = lootsplit.configuration
        return (
            hasattr(config, "split_mode")
            and config.split_mode == SplitMode.auction
        )


    def _compute_auction_payout(self, lootsplit: Lootsplit, winning_bid: int) -> tuple[int, int]:
        """Returns (guild_tax_amount, total_payout) once the winning bid is known.

        Formula:
        winning_bid + silver        = pre_guild_tax
        pre_guild_tax * guild_tax%  = guild_tax_amount
        pre_guild_tax - guild_tax   = total_payout
        """
        config = lootsplit.configuration
        pre_guild_tax = winning_bid + lootsplit.silver
        guild_tax_amount = round(pre_guild_tax * (config.guild_tax_percent / 100))
        total_payout = pre_guild_tax - guild_tax_amount
        return guild_tax_amount, total_payout


    def _compute_auction_min_bid(self, lootsplit: Lootsplit) -> int:
        """Min bid = (item_value - repair_cost) * (1 - min_bid_percent%)"""
        config = lootsplit.configuration
        value_after_repairs = lootsplit.item_value - lootsplit.repair_cost
        return round(value_after_repairs * (1 - config.auction_min_bid_percent / 100))

    async def revert_balances(self, lootsplit_id: int) -> None:
        lootsplit = await self.database_manager.get_lootsplit_by_id(
            lootsplit_id=lootsplit_id
        )
        if not lootsplit.paid_out:
            raise Exception("Lootsplit has not been paid out yet")
        amount_to_reverse = await self.get_lootsplit_value_per_player(lootsplit=lootsplit)
        await self.economy_manager.revert_balances(
            albion_character_ids=[
                player.albion_character_id for player in lootsplit.players
            ],
            amount=-amount_to_reverse,
        )
        lootsplit.paid_out = False
        await self.database_manager.save_or_update_lootsplit(lootsplit=lootsplit)

    async def create_split_sale(
        self, lootsplit_id: int, guild_discord_id: str
    ) -> SplitSale:
        config = await self.configuration_manager.get_config(guild_discord_id)
        deadline = datetime.now(timezone.utc) + timedelta(
            minutes=config.lootsplit_sale_timer_minutes
        )
        sale = SplitSale(lootsplit_id=lootsplit_id, deadline=deadline)
        await self.database_manager.save_or_update_split_sale(sale)
        return sale

    # -----------------------------------------------------------------------------
    # Embed builders
    # -----------------------------------------------------------------------------


    async def _build_lootsplit_embed(self,
        lootsplit: Lootsplit, auction: Optional[Auction]
    ) -> discord.Embed:
        config = lootsplit.configuration
        nb_players = len(lootsplit.players)
        is_auction = self._is_auction_mode(lootsplit)

        value_after_repairs, sale_tax_amount, guild_tax_amount, total_payout = await self._compute_lootsplit_payout(lootsplit)
        if not is_auction:
            
            total_payout_str = f"**{total_payout:,}**"
            per_player = round(total_payout / nb_players) if nb_players > 0 else 0
            per_player_str = f"**{per_player:,}**" if nb_players > 0 else "—"
            guild_tax_display = f"{guild_tax_amount:,}"
        else:
            if auction and auction.ended and auction.winning_bid is not None:
                auction_guild_tax, auction_total = self._compute_auction_payout(lootsplit, auction.winning_bid)
                total_payout_str = f"**{auction_total:,}**"
                per_player_str = (
                    f"**{round(auction_total / nb_players):,}**"
                    if nb_players > 0
                    else "—"
                )
                guild_tax_display = f"{auction_guild_tax:,}"
            else:
                total_payout_str = "N/A"
                per_player_str = "N/A"
                guild_tax_display = "N/A"

        status = "Paid Out" if lootsplit.paid_out else "Pending"
        color = discord.Color.green() if lootsplit.paid_out else discord.Color.orange()

        embed = discord.Embed(title=f"Loot Split #{lootsplit.id}", color=color)

        embed.add_field(name="Status", value=status, inline=False)
        embed.add_field(name="Item Value", value=f"{lootsplit.item_value:,}", inline=True)
        embed.add_field(name="Silver", value=f"{lootsplit.silver:,}", inline=True)
        embed.add_field(name="Repair Cost", value=f"{lootsplit.repair_cost:,}", inline=True)
        embed.add_field(name="Value After Repairs", value=f"{value_after_repairs:,}", inline=True)
        if not is_auction:
            embed.add_field(
                name=f"Sale Tax ({config.lootsplit_sale_tax_percent}%)",
                value=f"{sale_tax_amount:,}",
                inline=True,
            )
        embed.add_field(
            name=f"Guild Tax ({config.guild_tax_percent}%)",
            value=guild_tax_display,
            inline=True,
        )
        embed.add_field(name="Total Payout", value=total_payout_str, inline=True)
        embed.add_field(name="Players", value=str(nb_players), inline=True)
        embed.add_field(name="Per Player", value=per_player_str, inline=True)

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


    def _build_sale_embed(self, sale: SplitSale, lootsplit: Lootsplit) -> discord.Embed:
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


    def _build_auction_embed(self, auction: Auction, lootsplit: Lootsplit) -> discord.Embed:
        config = lootsplit.configuration
        value_after_repairs = lootsplit.item_value - lootsplit.repair_cost
        MIN_INCREMENT = 50000
        if auction.ended and auction.winner_id:
            color = discord.Color.green()
            title = f"Auction #{lootsplit.id} — Sold!"
        elif auction.ended:
            color = discord.Color.red()
            title = f"Auction #{lootsplit.id} — Ended (No Bids)"
        else:
            color = discord.Color.gold()
            title = f"Auction #{lootsplit.id} — Open"

        embed = discord.Embed(title=title, color=color)
        embed.add_field(name="Value After Repairs", value=f"**{value_after_repairs:,}**", inline=True)
        embed.add_field(name="Silver", value=f"**{lootsplit.silver:,}**", inline=True)
        embed.add_field(name="Minimum Bid", value=f"**{auction.min_bid+MIN_INCREMENT:,}**", inline=True)
        embed.add_field(name="# Bidders", value=str(len(auction.bids)), inline=True)

        if not auction.ended:
            deadline_ts = int(auction.deadline.replace(tzinfo=timezone.utc).timestamp())
            embed.add_field(name="Closing", value=f"<t:{deadline_ts}:R>", inline=False)

        if auction.bids:
            top_bid = max(auction.bids, key=lambda b: b.amount)
            embed.add_field(
                name="Current Top Bid",
                value=f"**{top_bid.amount:,}** silver",
                inline=False,
            )

        if auction.ended and auction.winner_id and auction.winning_bid is not None:
            guild_tax_amount, total_payout = self._compute_auction_payout(lootsplit, auction.winning_bid)
            nb_players = len(lootsplit.players)
            per_player = round(total_payout / nb_players) if nb_players > 0 else 0
            embed.add_field(
                name="Winner",
                value=(
                    f"<@{auction.winner_id}> — winning bid **{auction.winning_bid:,}** silver\n"
                    f"Guild Tax: **{guild_tax_amount:,}** ({config.guild_tax_percent}%)\n"
                    f"Total Payout: **{total_payout:,}** silver\n"
                    f"Per Player: **{per_player:,}** silver"
                ),
                inline=False,
            )
        elif not auction.ended:
            embed.set_footer(text="Bids are secret — only the top bid amount is shown publicly.")

        return embed


    async def _build_splits_list_embed(
        self,
        lootsplits: list[Lootsplit],
        target: discord.Member,
        page: int,
    ) -> discord.Embed:
        PAGE_SIZE = 10
        embed = discord.Embed(
            title=f"Loot Splits — {target.display_name}",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        start = page * PAGE_SIZE
        page_splits = lootsplits[start:start + PAGE_SIZE]

        for ls in page_splits:
            is_auction = self._is_auction_mode(ls)
            _, _, _, total_payout = await self._compute_lootsplit_payout(ls)

            if is_auction:
                per_player_str = "N/A"
            else:
                per_player_str = (
                    f"{round(total_payout / len(ls.players)):,}" if ls.players else "—"
                )

            status = "✅ Paid" if ls.paid_out else "⏳ Pending"

            if ls.discord_channel_id and ls.discord_message_id and ls.guild_discord_id:
                link = f"https://discord.com/channels/{ls.guild_discord_id}/{ls.discord_channel_id}/{ls.discord_message_id}"
                field_title = f"[Split #{ls.id}]({link})"
            else:
                field_title = f"Split #{ls.id}"

            embed.add_field(
                name=field_title,
                value=(
                    f"Status: **{status}**\n"
                    f"Per Player: **{per_player_str}**\n"
                    f"Players: {len(ls.players)}"
                ),
                inline=False,
            )

        total_pages = (len(lootsplits) + PAGE_SIZE - 1) // PAGE_SIZE
        embed.set_footer(text=f"Page {page + 1}/{total_pages}  •  {len(lootsplits)} splits total")
        return embed