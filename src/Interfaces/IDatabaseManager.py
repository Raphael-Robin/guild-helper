from abc import ABC, abstractmethod
from src.Model import Player, Log, Lootsplit, Configuration, SplitSale


class IDatabaseManager(ABC):
    @abstractmethod
    async def update_or_insert_player(
        self,
        albion_character_id: str,
        discord_user_id: str | None = None,
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
    async def revert_balances(
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

    @abstractmethod
    async def get_players_by_discord_id(self, discord_id: str) -> list[Player]:
        pass

    @abstractmethod
    async def get_or_create_players_from_characters(
        self, character_names: list[str]
    ) -> list[Player]:
        pass

    @abstractmethod
    async def get_configuration(self, guild_discord_server_id: str) -> Configuration:
        pass

    @abstractmethod
    async def save_or_update_configuration(self, config: Configuration) -> None:
        pass

    @abstractmethod
    async def get_lootsplit_by_message_id(self, message_id: str) -> Lootsplit | None:
        pass

    @abstractmethod
    async def get_logs_for_character(
        self, albion_character_name: str, limit: int, offset: int
    ) -> list[Log]:
        pass

    @abstractmethod
    async def get_all_logs(self) -> list[Log]:
        pass

    @abstractmethod
    async def save_or_update_split_sale(self, sale: SplitSale) -> None:
        pass

    @abstractmethod
    async def get_split_sale_by_lootsplit_id(
        self, lootsplit_id: int
    ) -> SplitSale | None:
        pass

    @abstractmethod
    async def get_split_sale_by_message_id(self, message_id: str) -> SplitSale | None:
        pass

    @abstractmethod
    async def get_expired_unended_sales(self) -> list[tuple[SplitSale, Lootsplit]]:
        pass


    @abstractmethod
    async def get_lootsplits_for_player(self, discord_user_id: str) -> list[Lootsplit]:
        pass

    @abstractmethod
    async def delete_lootsplit(self, lootsplit_id: int) -> None:
        pass