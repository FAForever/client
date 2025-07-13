from collections.abc import Mapping
from typing import Any
from typing import Literal
from typing import NotRequired
from typing import TypedDict

type ServerMessage = Mapping[str, Any]


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


class GPGCommand(TypedDict):
    command: str
    args: list[str | int | bool]


class PlayerRating(TypedDict):
    rating: list[int]
    number_of_games: int


type PlayerRatings = dict[str, PlayerRating]


class _Player(TypedDict):
    id: int
    login: str
    avatar: dict[str, str] | None
    country: str | None
    clan: str | None
    state: str | None
    ratings: PlayerRatings

    # deprecated
    global_rating: NotRequired[int]
    ladder_rating: NotRequired[int]
    number_of_games: NotRequired[int]


class WelcomeCommand(TypedDict):
    command: Literal["welcome"]
    me: _Player
    current_time: str

    # deprecated
    id: NotRequired[int]
    login: NotRequired[str]


class NoticeCommand(TypedDict):
    command: Literal["notice"]
    style: Literal["info", "error", "kill", "kick"]
    text: str


class AuthenticationFailedCommand(TypedDict):
    command: Literal["authentication_failed"]
    text: str


class InvalidCommand(TypedDict):
    command: Literal["invalid"]
