from abc import ABC, abstractmethod
from src.Model import Player, Lootsplit


class ILootsplitManager(ABC):
    @abstractmethod
    async def create_lootsplit(
        self, item_value: int, silver: int, repair_cost: int, guild_discord_id: str
    ) -> Lootsplit:
        pass

    @abstractmethod
    async def add_players(self, players: list[Player], lootsplit_id: int) -> None:
        pass

    @abstractmethod
    async def add_balances(self, lootsplit_id: int) -> None:
        pass

    @abstractmethod
    def get_lootsplit_value_per_player(self, lootsplit: Lootsplit) -> int:
        pass

    @abstractmethod
    async def add_players_by_name(
        self, character_names: list[str], lootsplit_id: int
    ) -> None:
        pass

    @abstractmethod
    async def reverse_balances(self, lootsplit_id: int) -> None:
        pass
