from abc import ABC, abstractmethod
from src.Model import Player


class IEconomyManager(ABC):
    @abstractmethod
    def get_balance(self, player: Player) -> int:
        pass

    @abstractmethod
    def add_balance(self, player: Player, amount: int):
        pass

    @abstractmethod
    def remove_balance(self, player: Player, amount: int):
        pass

    @abstractmethod
    def get_alltime_balance(self, player: Player) -> int:
        pass

    @abstractmethod
    def get_players_with_highest_balance(self) -> list[Player]:
        pass

    @abstractmethod
    def get_players_with_highest_alltime_balance(self) -> list[Player]:
        pass
