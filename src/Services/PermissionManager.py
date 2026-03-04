from src.Interfaces import IPermissionManager, IDatabaseManager, IAlbionApiManager
from src.Model import Player, Guild, Alliance


class PermissionManager(IPermissionManager):
    def __init__(
        self, database_manager: IDatabaseManager, albion_api_manager: IAlbionApiManager
    ) -> None:
        self.database_manager = database_manager
        self.albion_api_manager = albion_api_manager

    async def register_albion_character(
        self, discord_user_id: str, albion_character_name: str
    ) -> None:

        await self.database_manager.update_or_insert_player(
            albion_character_id=await self.albion_api_manager.get_player_id_by_name(
                player_name=albion_character_name
            ),
            albion_character_name=albion_character_name,
            discord_user_id=discord_user_id,
        )

    async def is_player_in_alliance(self, player: Player, alliance: Alliance) -> bool:
        player_alliance = self.albion_api_manager.get_player_alliance(player=player)
        return player_alliance == alliance

    async def is_player_in_guild(self, player: Player, guild: Guild) -> bool:
        player_guild = self.albion_api_manager.get_player_guild(player=player)
        return player_guild == guild

    async def get_character_info(self, character_name: str) -> dict | None:
        try:
            player = await self.albion_api_manager.get_player_by_name(character_name)
        except Exception:
            return None

        try:
            guild = await self.albion_api_manager.get_player_guild(player=player)
        except Exception:
            guild = None

        try:
            alliance = await self.albion_api_manager.get_player_alliance(player=player)
        except Exception:
            alliance = None  # Player has no alliance — perfectly normal

        return {
            "name": player.albion_character_name,
            "guild": guild.name if guild else "N/A",
            "alliance": alliance.name if alliance else "N/A",
        }

    async def is_character_already_registered(self, albion_character_name: str) -> bool:
        players = await self.database_manager.get_players(
            albion_character_name=albion_character_name
        )
        if not players:
            return False
        player = players[0]
        return player.discord_user_id is not None
