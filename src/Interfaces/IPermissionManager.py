from abc import ABC, abstractmethod


class IPermissionManager(ABC):
    @abstractmethod
    async def register_albion_character(
        self, discord_user_id: str, albion_character_name: str
    ) -> None:
        pass

    @abstractmethod
    async def get_character_info(self, albion_character_name:str) -> dict[str,str]:
        pass
