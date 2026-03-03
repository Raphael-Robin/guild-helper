from abc import ABC, abstractmethod
from src.Model import Player, Log, Lootsplit


class IDatabaseManager(ABC):
    @abstractmethod
    async def update_or_insert_player(
        self,
        discord_user_id: str,
        albion_character_id: str | None = None,
        albion_character_name: str | None = None,
    ) -> None:
        pass

    @abstractmethod
    async def update_balance(self, albion_character_id: str, amount: int) -> None:
        pass

    @abstractmethod
    async def update_balances(
        self, albion_character_id: list[str], amount: int
    ) -> None:
        pass

    @abstractmethod
    async def get_players(
        self,
        discord_user_id: str | None = None,
        albion_character_id: str | None = None,
        albion_character_name: str | None = None,
    ) -> list[Player]:
        pass

    @abstractmethod
    async def get_top_balance_players(
        self, nb_players: int, offset: int
    ) -> list[Player]:
        pass

    @abstractmethod
    async def get_top_all_time_balance_players(
        self, nb_players: int, offset: int
    ) -> list[Player]:
        pass

    @abstractmethod
    async def save_economy_log(self, log: Log) -> None:
        pass

    @abstractmethod
    async def get_lootsplit_by_id(self, lootsplit_id: int) -> Lootsplit:
        pass

    @abstractmethod
    async def save_or_update_lootsplit(self, lootsplit: Lootsplit) -> None:
        pass