from src.Interfaces import (
    ILootsplitManager,
    IConfigurationManager,
    IDatabaseManager,
    IEconomyManager,
)
from src.Model import Player, Lootsplit


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
        lootsplit.players.extend(
            [player for player in players if player not in lootsplit.players]
        )
        await self.database_manager.save_or_update_lootsplit(lootsplit=lootsplit)

    async def add_players(self, players: list[Player], lootsplit_id: int) -> None:
        lootsplit = await self.database_manager.get_lootsplit_by_id(
            lootsplit_id=lootsplit_id
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
        total_value = self.get_lootsplit_value_total(lootsplit=lootsplit)
        nb_players = len(lootsplit.players)
        return round(total_value / nb_players)

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
