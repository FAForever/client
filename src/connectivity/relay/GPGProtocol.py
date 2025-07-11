from enum import Enum
from typing import NamedTuple
from typing import Protocol


# GameState as sent by FA, ENDED was added by the FAF project
class GameState(Enum):
    NONE = "None"
    IDLE = "Idle"
    LOBBY = "Lobby"
    LAUNCHING = "Launching"
    ENDED = "Ended"


class LobbyInitMode(Enum):
    NORMAL = 0
    AUTO = 1


class GPGFieldType(Enum):
    INT = 0
    STRING = 1


class GPGMessage(Protocol):
    def command(self) -> str: ...
    def arguments(self) -> list[str | int]: ...


class GameStateMessage(NamedTuple):
    state: GameState

    def command(self) -> str:
        return "GameState"

    def arguments(self) -> list[str | int]:
        return [self.state.value]


class GameEnded:
    def command(self) -> str:
        return "GameEnded"

    def arguments(self) -> list[str | int]:
        return []


class GameFull:
    def command(self) -> str:
        return "GameFull"

    def arguments(self) -> list[str | int]:
        return []


class CreateLobby(NamedTuple):
    mode: LobbyInitMode
    port: int
    player_name: str
    player_id: int

    def command(self) -> str:
        return "CreateLobby"

    def arguments(self) -> list[str | int]:
        return [self.mode.value, self.port, self.player_name, self.player_id, 1]


class JoinGame(NamedTuple):
    remote_player_login: str
    remote_player_id: int

    def command(self) -> str:
        return "JoinGame"

    def arguments(self) -> list[str | int]:
        return ["127.0.0.1:0", self.remote_player_login, self.remote_player_id]


class HostGame(NamedTuple):
    map_name: str

    def command(self) -> str:
        return "HostGame"

    def arguments(self) -> list[str | int]:
        return [self.map_name]


class ConnectToPeer(NamedTuple):
    remote_player_login: str
    remote_player_id: int

    def command(self) -> str:
        return "ConnectToPeer"

    def arguments(self) -> list[str | int]:
        return ["127.0.0.1:0", self.remote_player_login, self.remote_player_id]


class DisconnectFromPeer(NamedTuple):
    remote_player_id: int

    def command(self) -> str:
        return "DisconnectFromPeer"

    def arguments(self) -> list[str | int]:
        return [self.remote_player_id]


class Generic(NamedTuple):
    command_name: str
    args: list[str | int]

    def command(self) -> str:
        return self.command_name

    def arguments(self) -> list[str | int]:
        return self.args.copy()
