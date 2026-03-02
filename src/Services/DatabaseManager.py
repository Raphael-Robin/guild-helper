from src.Interfaces import IDatabaseManager, IAlbionApiManager
from src.Model import Player
from pymongo import AsyncMongoClient


class DatabaseManager(IDatabaseManager):
    def __init__(
        self, database_url: str, albion_api_manager: IAlbionApiManager
    ) -> None:
        self.client = AsyncMongoClient(host=database_url)
        self.data_base = self.client["guild-helper"]
        self.albion_api_manager = albion_api_manager

    async def update_or_insert_player(
        self,
        discord_user_id: str,
        albion_character_id: str | None = None,
        albion_character_name: str | None = None,
    ) -> None:

        if not albion_character_id and not albion_character_name:
            raise Exception(
                "You must provide either the character Id or the Character Name"
            )

        if not albion_character_id and albion_character_name:
            albion_character_id = await self.albion_api_manager.get_player_id_by_name(
                player_name=albion_character_name
            )

        if albion_character_id and not albion_character_name:
            albion_character_name = await self.albion_api_manager.get_player_name_by_id(
                player_id=albion_character_id
            )

        await self.data_base["players"].update_one(
            filter={"albion_character_id": albion_character_id},
            update={
                "$set": {"discord_user_id": discord_user_id},
                "$setOnInsert": {
                    "albion_character_name": albion_character_name,
                    "balance": 0,
                    "all_time_balance": 0,
                },
            },
            upsert=True,
        )

    async def update_balance(self, albion_character_id: str, amount: int) -> None:
        await self.update_balances(
            albion_character_id=[albion_character_id], amount=amount
        )

    async def update_balances(
        self, albion_character_id: list[str], amount: int
    ) -> None:
        query = {"albion_character_id": {"$in": albion_character_id}}

        if amount > 0:
            update = {"$inc": {"balance": amount, "all_time_balance": amount}}
        else:
            update = {"$inc": {"balance": amount}}

        await self.data_base["players"].update_many(filter=query, update=update)

    async def get_players(
        self,
        discord_user_id: str | None = None,
        albion_character_id: str | None = None,
        albion_character_name: str | None = None,
    ) -> list[Player]:

        if not (discord_user_id or albion_character_id or albion_character_name):
            raise Exception("You need to provide at least one identifying information")

        if albion_character_name:
            filter = {"albion_character_name": albion_character_name}
        elif albion_character_id:
            filter = {"albion_character_id": albion_character_id}
        else:
            filter = {"discord_user_id": discord_user_id}

        players = [
            Player.model_validate(player)
            for player in await self.data_base["players"].find(filter).to_list()
        ]

        return players
