from src.Exceptions.player_not_found import PlayerNotFound
from src.Interfaces import IAlbionApiManager
from src.Model import Player, Guild, Alliance
import requests


class AlbionApiManager(IAlbionApiManager):
    def __init__(self, region: str = "europe"):
        # Select base URL based on region
        regions = {
            "americas": "https://gameinfo.albiononline.com/api/gameinfo",
            "europe": "https://gameinfo-ams.albiononline.com/api/gameinfo",
            "asia": "https://gameinfo-sgp.albiononline.com/api/gameinfo",
        }
        self.base_url = regions.get(region.lower(), regions["americas"])
        self.session = requests.Session()
        # The API often requires a User-Agent to avoid 403 blocks
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

    async def get_player_id_by_name(self, player_name: str) -> str:
        player = await self.get_player_by_name(player_name=player_name)
        return player.albion_character_id

    async def get_player_name_by_id(self, player_id: str) -> str:
        query = f"{self.base_url}/players/{player_id}"
        response = self.session.get(query)
        if response.status_code == 200:
            data = response.json()
            return data["Name"]
        raise Exception()

    async def get_player_guild(self, player: Player) -> Guild:
        query = f"{self.base_url}/players/{player.albion_character_id}"
        response = self.session.get(query)
        if response.status_code == 200:
            data = response.json()
            return Guild(name=data["GuildName"], id=data["GuildId"])
        raise Exception()

    async def get_player_alliance(self, player: Player) -> Alliance:
        query = f"{self.base_url}/players/{player.albion_character_id}"
        response = self.session.get(query)
        if response.status_code == 200:
            data = response.json()
            return await self.get_alliance_by_id(data["AllianceId"])
        raise Exception()

    async def get_alliance_by_id(self, alliance_id: str) -> Alliance:
        query = f"{self.base_url}/alliances/{alliance_id}"
        response = self.session.get(query)

        guilds = []
        if response.status_code == 200:
            data = response.json()

            alliance_name, alliance_id, alliance_tag = (
                data["AllianceName"],
                data["AllianceId"],
                data["AllianceTag"],
            )
            for guild in data["Guilds"]:
                guilds.append(Guild(name=guild["Name"], id=guild["Id"]))
            return Alliance(
                name=alliance_name, tag=alliance_tag, id=alliance_id, guilds=guilds
            )
        raise Exception(f"response.status_code: {response.status_code}")

    async def get_guild_alliance(self, guild: Guild) -> Alliance:
        query = f"{self.base_url}/guilds/{guild.id}"
        response = self.session.get(query)
        if response.status_code == 200:
            data = response.json()
            alliance_id = data["AllianceId"]
            return await self.get_alliance_by_id(alliance_id=alliance_id)
        raise Exception()

    async def get_guild_by_name(self, guild_name: str) -> Guild:
        query = f"{self.base_url}/search"
        params = {"q": guild_name}
        response = self.session.get(query, params=params)
        if response.status_code == 200:
            data = response.json()
            for p_data in data.get("guilds", []):
                if p_data["Name"].lower() == guild_name.lower():
                    return Guild.model_validate(
                        {"name": p_data["Name"], "id": p_data["Id"]}
                    )
        raise Exception()

    async def get_player_by_name(self, player_name: str) -> Player:
        query = f"{self.base_url}/search"
        params = {"q": player_name}
        response = self.session.get(query, params=params)
        if response.status_code == 200:
            data = response.json()
            for p_data in data.get("players", []):
                if p_data["Name"].lower() == player_name.lower():
                    return Player.model_validate(
                        {
                            "albion_character_name": p_data["Name"],
                            "albion_character_id": p_data["Id"],
                        }
                    )
        raise PlayerNotFound(player_name)
