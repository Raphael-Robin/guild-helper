from src.Interfaces import ILootsplitManager, IConfigurationManager, IDatabaseManager, IEconomyManager
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
        self, item_value: int, silver: int, repair_cost: int
    ) -> Lootsplit:
        return Lootsplit(
            configuration=await self.configuration_manager.get_config(),
            players=[],
            item_value=item_value,
            silver=silver,
            repair_cost=repair_cost,
        )

    async def add_players(self, players: list[Player], lootsplit_id: int) -> None:
        lootsplit = await self.database_manager.get_lootsplit_by_id(lootsplit_id=lootsplit_id)
        lootsplit.players.extend(players)
        await self.database_manager.save_or_update_lootsplit(lootsplit=lootsplit)


    async def add_balances(self, lootsplit_id: int) -> None:
        lootsplit = await self.database_manager.get_lootsplit_by_id(lootsplit_id=lootsplit_id)
        await self.economy_manager.add_balances(
            albion_character_ids=[player.albion_character_id for player in lootsplit.players], 
            amount=self.get_lootsplit_value_per_player(lootsplit=lootsplit))

    def get_lootsplit_value_total(self, lootsplit:Lootsplit) -> int:
        return round((lootsplit.item_value + lootsplit.silver - lootsplit.repair_cost) * (lootsplit.configuration.guild_tax_percent / 100))
    
    def get_lootsplit_value_per_player(self, lootsplit: Lootsplit) -> int:
        total_value = self.get_lootsplit_value_total(lootsplit=lootsplit)
        nb_players = len(lootsplit.players)
        return round(total_value / nb_players)