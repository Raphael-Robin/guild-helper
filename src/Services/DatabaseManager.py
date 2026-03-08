from datetime import datetime, timezone

from src.Exceptions.player_not_found import PlayerNotFound
from src.Interfaces import IDatabaseManager, IAlbionApiManager
from src.Model import Player, Log, Lootsplit, Configuration, SplitSale
from pymongo import AsyncMongoClient


class DatabaseManager(IDatabaseManager):
    def __init__(
        self, database_url: str, albion_api_manager: IAlbionApiManager, database_name: str
    ) -> None:
        self.client = AsyncMongoClient(host=database_url)
        self.data_base = self.client[database_name]
        self.economy_logs = self.data_base["economy_logs"]
        self.lootsplits = self.data_base["lootsplits"]
        self.players = self.data_base["players"]
        self.albion_api_manager = albion_api_manager

    async def setup(self):
        await self.data_base.counters.update_one(
            {"_id": "lootsplit_id"}, {"$setOnInsert": {"seq": 0}}, upsert=True
        )
        await self.data_base.economy_logs.find({}).to_list()

    async def update_or_insert_player(
        self,
        albion_character_id: str,
        discord_user_id: str | None = None,
        albion_character_name: str | None = None,
    ) -> None:

        if not albion_character_name:
            albion_character_name = await self.albion_api_manager.get_player_name_by_id(
                player_id=albion_character_id
            )

        await self.players.update_one(
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

        await self.players.update_many(filter=query, update=update)

    async def revert_balances(
        self, albion_character_id: list[str], amount: int
    ) -> None:
        query = {"albion_character_id": {"$in": albion_character_id}}
        update = {"$inc": {"balance": amount, "all_time_balance": amount}}
        await self.players.update_many(filter=query, update=update)

    async def get_players(
        self,
        discord_user_id: str | None = None,
        albion_character_id: str | None = None,
        albion_character_name: str | None = None,
    ) -> list[Player]:

        if not (discord_user_id or albion_character_id or albion_character_name):
            raise Exception("You need to provide at least one identifying information")

        if albion_character_name:
            filter = {
                "albion_character_name": {
                    "$regex": f"^{albion_character_name}$",
                    "$options": "i",
                }
            }
        elif albion_character_id:
            filter = {"albion_character_id": albion_character_id}
        else:
            filter = {"discord_user_id": discord_user_id}

        players = [
            Player.model_validate(player)
            for player in await self.players.find(filter).to_list()
        ]

        return players

    async def get_top_balance_players(
        self, nb_players: int, offset: int
    ) -> list[Player]:
        players_cursor = (
            self.players.find({}).sort("balance", -1).skip(offset).limit(nb_players)
        )
        players = []
        async for player in players_cursor:
            players.append(Player.model_validate(player))
        return players

    async def get_top_all_time_balance_players(
        self, nb_players: int, offset: int
    ) -> list[Player]:
        players_cursor = (
            self.players.find({})
            .sort("all_time_balance", -1)
            .skip(offset)
            .limit(nb_players)
        )
        players = []
        async for player in players_cursor:
            players.append(Player.model_validate(player))
        return players

    async def save_economy_log(self, log: Log) -> None:
        await self.economy_logs.insert_one(log.model_dump(mode="json"))

    async def get_lootsplit_by_id(self, lootsplit_id: int) -> Lootsplit:
        document = await self.lootsplits.find_one({"_id": lootsplit_id})
        if document is None:
            raise Exception(f"Lootsplit with id {lootsplit_id} not found")
        return Lootsplit.model_validate(document)

    async def save_or_update_lootsplit(self, lootsplit: Lootsplit) -> None:
        if lootsplit.id is None:
            lootsplit.id = await self.get_next_sequence_value("lootsplit_id")

        data = lootsplit.model_dump(by_alias=True, exclude_none=True)

        await self.lootsplits.update_one(
            filter={"_id": lootsplit.id},
            update={"$set": data, "$setOnInsert": {"seq": 0}},
            upsert=True,
        )

    async def get_next_sequence_value(self, sequence_name: str) -> int:
        """Atomically increments and returns the next ID."""
        result = await self.data_base.counters.find_one_and_update(
            {"_id": sequence_name},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True,
        )
        return result["seq"]  # type: ignore

    async def get_players_by_discord_id(self, discord_id: str) -> list[Player]:
        player_dicts = await self.players.find(
            {"discord_user_id": discord_id}
        ).to_list()
        return [Player.model_validate(player) for player in player_dicts]

    async def get_or_create_players_from_characters(
        self, character_names: list[str]
    ) -> list[Player]:
        players = []
        for name in character_names:
            player_list = await self.get_players(albion_character_name=name)
            if not player_list:
                albion_character_id = (
                    await self.albion_api_manager.get_player_id_by_name(
                        player_name=name
                    )
                )
                await self.update_or_insert_player(
                    albion_character_id=albion_character_id,
                    albion_character_name=name,
                )
                player_list = await self.get_players(albion_character_name=name)
            if player_list:
                players.append(player_list[0])
            else:
                raise PlayerNotFound(name)
        return players

    async def get_configuration(self, guild_discord_server_id: str) -> Configuration:
        document = await self.data_base["configurations"].find_one(
            {"guild_discord_server_id": guild_discord_server_id}
        )
        if document is None:
            config = Configuration(guild_discord_server_id=guild_discord_server_id)
            await self.save_or_update_configuration(config)
            return config
        return Configuration.model_validate(document)

    async def save_or_update_configuration(self, config: Configuration) -> None:
        await self.data_base["configurations"].update_one(
            {"guild_discord_server_id": config.guild_discord_server_id},
            {"$set": config.model_dump()},
            upsert=True,
        )

    async def get_lootsplit_by_message_id(self, message_id: str) -> Lootsplit | None:
        document = await self.lootsplits.find_one({"discord_message_id": message_id})
        if document is None:
            return None
        return Lootsplit.model_validate(document)

    async def get_logs_for_character(
        self, albion_character_name: str, limit: int, offset: int
    ) -> list[Log]:
        cursor = (
            self.economy_logs.find(
                {
                    "player.albion_character_name": {
                        "$regex": f"^{albion_character_name}$",
                        "$options": "i",
                    }
                }
            )
            .sort("created_at", -1)
            .skip(offset)
            .limit(limit)
        )
        return [Log.model_validate(log) async for log in cursor]

    async def get_all_logs(self) -> list[Log]:
        cursor = self.economy_logs.find({}).sort("created_at", -1)
        return [Log.model_validate(log) async for log in cursor]

    async def save_or_update_split_sale(self, sale: SplitSale) -> None:
        if sale.id is None:
            sale.id = await self.get_next_sequence_value("split_sale_id")
        data = sale.model_dump(by_alias=True, exclude_none=True)
        await self.data_base["split_sales"].update_one(
            {"_id": sale.id},
            {"$set": data},
            upsert=True,
        )

    async def get_split_sale_by_lootsplit_id(
        self, lootsplit_id: int
    ) -> SplitSale | None:
        doc = await self.data_base["split_sales"].find_one(
            {"lootsplit_id": lootsplit_id}
        )
        return SplitSale.model_validate(doc) if doc else None

    async def get_split_sale_by_message_id(self, message_id: str) -> SplitSale | None:
        doc = await self.data_base["split_sales"].find_one(
            {"discord_message_id": message_id}
        )
        return SplitSale.model_validate(doc) if doc else None

    async def get_expired_unended_sales(self) -> list[tuple[SplitSale, Lootsplit]]:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cursor = self.data_base["split_sales"].find(
            {
                "ended": False,
            }
        )
        results = []
        async for doc in cursor:
            sale = SplitSale.model_validate(doc)
            if sale.deadline < now:
                lootsplit = await self.get_lootsplit_by_id(sale.lootsplit_id)
                results.append((sale, lootsplit))
        return results
