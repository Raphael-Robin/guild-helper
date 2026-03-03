from src.Interfaces import ILootsplitManager, IConfigurationManager, IDatabaseManager
from src.Model import Player, Lootsplit


class LootsplitManager(ILootsplitManager):
    def __init__(
        self,
        configuration_manager: IConfigurationManager,
        database_manager: IDatabaseManager,
    ) -> None:
        self.configuration_manager = configuration_manager
        self.database_manager = database_manager

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

    def add_players(self, players: list[Player]) -> None:
        pass

    def add_balances(self) -> None:
        pass
