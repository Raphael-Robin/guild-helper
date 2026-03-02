from src.Interfaces import IAlbionApiManager
from src.Model import Player
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
        query = f"{self.base_url}/search"
        params = {"q": player_name}
        response = self.session.get(query, params=params)
        if response.status_code == 200:
            data = response.json()
            # Search returns a list of players; find the exact match
            for p_data in data.get("players", []):
                if p_data["Name"].lower() == player_name.lower():
                    return p_data["Id"]
        raise Exception()

    async def get_player_guild_id(self, Player: Player) -> str:
        pass
