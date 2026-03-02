from src.Interfaces import IPermissionManager, IDatabaseManager


class PermissionManager(IPermissionManager):
    def __init__(self, database_manager: IDatabaseManager) -> None:
        self.database_manager = database_manager

    async def register_albion_character(
        self, discord_user_id: str, albion_character_id: str
    ) -> None:

        await self.database_manager.update_or_insert_player(
            albion_character_id=albion_character_id, discord_user_id=discord_user_id
        )
