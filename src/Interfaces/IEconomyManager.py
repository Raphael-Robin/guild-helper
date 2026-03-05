from abc import ABC, abstractmethod
from src.Model import Player


class IEconomyManager(ABC):
    @abstractmethod
    async def get_balance(self, discord_user_id: str) -> int:
        pass

    @abstractmethod
    async def add_balances(self, albion_character_ids: list[str], amount: int) -> None:
        pass

    @abstractmethod
    async def revert_balances(
        self, albion_character_ids: list[str], amount: int
    ) -> None:
        pass

    @abstractmethod
    async def remove_balance(self, discord_user_id: str, amount: int) -> None:
        pass

    @abstractmethod
    async def get_alltime_balance(self, discord_user_id: str) -> int:
        pass

    @abstractmethod
    async def get_players_with_highest_balance(
        self, nb_players: int, offset: int
    ) -> list[Player]:
        pass

    @abstractmethod
    async def get_players_with_highest_alltime_balance(
        self, nb_players: int, offset: int
    ) -> list[Player]:
        pass
