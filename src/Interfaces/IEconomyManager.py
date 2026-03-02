from abc import ABC, abstractmethod
from src.Model import Player, Lootsplit


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
