from datetime import datetime, timedelta, timezone

from src.Interfaces import (
    ILootsplitManager,
    IConfigurationManager,
    IDatabaseManager,
    IEconomyManager,
)
from src.Model import Player, Lootsplit, SplitSale


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
        amount = self.get_lootsplit_value_per_player(lootsplit=lootsplit)
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

    def get_lootsplit_value_per_player(self, lootsplit: Lootsplit) -> int:
        gross = lootsplit.item_value + lootsplit.silver
        after_repairs = gross - lootsplit.repair_cost
        sale_tax_amount = round(
            after_repairs * (lootsplit.configuration.lootsplit_sale_tax_percent / 100)
        )
        guild_tax_amount = round(
            after_repairs * (lootsplit.configuration.guild_tax_percent / 100)
        )
        after_taxes = after_repairs - sale_tax_amount - guild_tax_amount
        total_payout = after_taxes
        nb_players = len(lootsplit.players)
        per_player = round(total_payout / nb_players) if nb_players > 0 else 0
        return per_player

    async def revert_balances(self, lootsplit_id: int) -> None:
        lootsplit = await self.database_manager.get_lootsplit_by_id(
            lootsplit_id=lootsplit_id
        )
        if not lootsplit.paid_out:
            raise Exception("Lootsplit has not been paid out yet")
        amount_to_reverse = self.get_lootsplit_value_per_player(lootsplit=lootsplit)
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
