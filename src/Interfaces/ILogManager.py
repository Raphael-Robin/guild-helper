from abc import ABC, abstractmethod
from src.Model import Log


class ILogManager(ABC):
    @abstractmethod
    async def log_economy(self, log: Log) -> None:
        pass
