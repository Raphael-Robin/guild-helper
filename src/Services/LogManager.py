from src.Interfaces import ILogManager, IDatabaseManager
from src.Model import Log


class LogManager(ILogManager):
    def __init__(self, database_manager: IDatabaseManager) -> None:
        self.database_manager = database_manager

    async def log_economy(self, log: Log) -> None:
        await self.database_manager.save_economy_log(log)
