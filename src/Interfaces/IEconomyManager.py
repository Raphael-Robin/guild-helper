from abc import ABC, abstractmethod
from src.Model import Player


class IEconomyManager(ABC):
    @abstractmethod
    async def get_balance(self, discord_user_id: str) -> int:
        pass

    @abstractmethod
    async def add_balance(self, albion_character_ids: list[str], amount: int) -> None:
        pass

    @abstractmethod
    async def remove_balance(self, discord_user_id: str, amount: int) -> None:
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
