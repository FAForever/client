from typing import Any
from typing import Literal
from typing import NotRequired
from typing import TypedDict

type ServerMessage = dict[str, Any]


class GameJoinFailedCommand(TypedDict):
    command: Literal["game_join_failed"]
    reason: Literal["game_not_ready", "host_left_game", "bad_password"]
    uid: int


class GameLaunchCommand(TypedDict):
    command: Literal["game_launch"]
    args: list[str | int]
    uid: int
    mod: str
    game_type: str
    name: str
    rating_type: str

    init_mode: NotRequired[int]
    mapname: NotRequired[str]
    team: NotRequired[int]
    faction: NotRequired[int]
    expected_players: NotRequired[int]
    map_position: NotRequired[int]
    game_options: NotRequired[dict[str, Any]]


class MatchFoundCommand(TypedDict):
    command: Literal["match_found"]
    queue_name: str


class SocialCommand(TypedDict):
    command: Literal["social"]
    autojoin: list[str]
    channels: NotRequired[list[str]]
    friends: NotRequired[list[int]]
    foes: NotRequired[list[int]]
    power: NotRequired[int]
