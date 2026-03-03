from src.Interfaces import IEconomyManager, ILogManager, IDatabaseManager
from src.Model import Player, Log, Action


class EconomyManager(IEconomyManager):
    def __init__(
        self, database_manager: IDatabaseManager, logger: ILogManager | None = None
    ) -> None:
        self.logger = logger
        self.database_manager = database_manager

    async def get_balance(self, discord_user_id: str) -> int:
        players = await self.database_manager.get_players(
            discord_user_id=discord_user_id
        )
        balance = 0
        for player in players:
            balance += player.balance

        return balance

    async def add_balance(self, albion_character_ids: list[str], amount: int) -> None:
        if not amount > 0 or not albion_character_ids:
            return
        for albion_character_id in albion_character_ids:
            player = (
                await self.database_manager.get_players(
                    albion_character_id=albion_character_id
                )
            )[0]

            if self.logger:
                log = Log(player=player, action=Action.add, amount=amount)
                self.logger.log_economy(log=log)

        await self.database_manager.update_balances(albion_character_ids, amount=amount)

    async def remove_balance(self, discord_user_id: str, amount: int) -> None:
        players = await self.database_manager.get_players(
            discord_user_id=discord_user_id
        )
        total_balance = sum(player.balance for player in players)

        if amount < 0 or total_balance < amount:
            return
        else:
            for player in players:
                balance_to_remove = min(player.balance, amount)
                amount -= balance_to_remove

                if self.logger:
                    log = Log(player=player, action=Action.add, amount=amount)
                    self.logger.log_economy(log=log)

                await self.database_manager.update_balance(
                    player.albion_character_id, -balance_to_remove
                )

    async def get_alltime_balance(self, player: Player) -> int:
        pass

    async def get_players_with_highest_balance(self) -> list[Player]:
        pass

    def get_players_with_highest_alltime_balance(self) -> list[Player]:
        pass
