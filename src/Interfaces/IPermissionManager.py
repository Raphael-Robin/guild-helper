from abc import ABC, abstractmethod


class IPermissionManager(ABC):
    @abstractmethod
    async def register_albion_character(
        self, discord_user_id: str, albion_character_id: str
    ) -> None:
        pass
