from abc import ABC, abstractmethod
from src.Model import Configuration


class IConfigurationManager(ABC):
    @abstractmethod
    async def get_config(self) -> Configuration:
        pass
