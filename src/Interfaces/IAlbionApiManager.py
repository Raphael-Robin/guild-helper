from abc import ABC, abstractmethod
from src.Model import Player, Guild, Alliance

class IAlbionApiManager(ABC):

    @abstractmethod
    def get_player_by_name(self, player_name: str) -> Player:
        pass

    @abstractmethod
    def get_player_guild(self, Player: Player) -> Guild:
        pass

    @abstractmethod
    def is_player_in_guild(self, player:Player, guild: Guild) -> bool:
        pass

    @abstractmethod
    def is_player_in_alliance(self, player:Player, guild: Alliance) -> bool:
        pass