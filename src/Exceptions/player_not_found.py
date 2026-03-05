class PlayerNotFound(Exception):
    def __init__(self, player_name: str, *args: object) -> None:
        super().__init__(f"Could not find player {player_name}", *args)
