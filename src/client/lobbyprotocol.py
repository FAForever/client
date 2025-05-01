from typing import Literal
from typing import TypedDict


class GameJoinFailedCommand(TypedDict):
    command: Literal["game_join_failed"]
    reason: Literal["game_not_ready", "host_left_game", "bad_password"]
    uid: int
