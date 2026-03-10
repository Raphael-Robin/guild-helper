from abc import ABC, abstractmethod
from typing import Optional

import discord
from src.Model import Player, Lootsplit, SplitSale, Auction


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
    async def get_lootsplit_value_per_player(self, lootsplit: Lootsplit) -> int:
        pass

    @abstractmethod
    async def add_players_by_name(
        self, character_names: list[str], lootsplit_id: int
    ) -> None:
        pass

    @abstractmethod
    async def revert_balances(self, lootsplit_id: int) -> None:
        pass

    @abstractmethod
    async def create_split_sale(self, lootsplit_id: int, guild_discord_id: str) -> SplitSale:
        pass

    @abstractmethod
    async def _build_lootsplit_embed(self,lootsplit: Lootsplit, auction: Optional[Auction]) -> discord.Embed:
        pass

    @abstractmethod
    def _build_sale_embed(self, sale: SplitSale, lootsplit: Lootsplit) -> discord.Embed:
        pass

    @abstractmethod
    def _build_auction_embed(self, auction: Auction, lootsplit: Lootsplit) -> discord.Embed:
        pass

    @abstractmethod
    async def _build_splits_list_embed(self,lootsplits: list[Lootsplit],target: discord.Member,page: int,) -> discord.Embed:
        pass

    @abstractmethod
    async def _compute_lootsplit_payout(self, lootsplit: Lootsplit) -> tuple[int, int, int, int]:
        pass

    @abstractmethod
    def _is_auction_mode(self, lootsplit: Lootsplit) -> bool:
        pass

    @abstractmethod
    def _compute_auction_payout(self, lootsplit: Lootsplit, winning_bid: int) -> tuple[int, int]:
        pass

    @abstractmethod
    def _compute_auction_min_bid(self, lootsplit: Lootsplit) -> int:
        pass