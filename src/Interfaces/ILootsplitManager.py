from abc import ABC, abstractmethod
from src.Model import Player, Lootsplit


class ILootsplitManager(ABC):
    @abstractmethod
    def create_lootsplit(
        self, item_value: int, silver: int, repair_cost: int
    ) -> Lootsplit:
        pass

    @abstractmethod
    def add_players(self, players: list[Player]) -> None:
        pass

    @abstractmethod
    def add_balances(self) -> None:
        pass
