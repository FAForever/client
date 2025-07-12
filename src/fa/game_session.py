import logging
from enum import IntEnum
from typing import Any

from PyQt6.QtCore import QObject
from PyQt6.QtCore import QProcess
from PyQt6.QtCore import pyqtSignal

from src import client
from src.config import setup_file_handler
from src.connectivity.IceAdapterClient import IceAdapterClient
from src.connectivity.IceAdapterManager import IceAdapterManager
from src.connectivity.IceAdapterProcess import IceAdapterProcess
from src.connectivity.IceServersPoller import IceServersPoller
from src.connectivity.relay.GPGNetServer import GPGNetServer
from src.connectivity.relay.GPGProtocol import LobbyInitMode
from src.fa.game_process import instance as game_process_instance
from src.qt.utils import tcp_server

logger = logging.getLogger(__name__)
# Log to a separate file to not pollute normal log with huge json dumps
logger.propagate = False
logger.addHandler(setup_file_handler("gamesession.log"))


class GameSessionState(IntEnum):
    # Game services are entirely off
    OFF = 0
    # We're listening on the game port
    LISTENING = 1
    # We've verified our connectivity and are idle
    IDLE = 2
    # Game has been launched but we're not connected yet
    LAUNCHED = 3
    # Game is running and we're relaying gpgnet commands
    RUNNING = 4


class GameSession(QObject):
    ready = pyqtSignal(int)
    gameFullSignal = pyqtSignal()
    game_launched = pyqtSignal()

    def __init__(self, player_id: int, player_login: str) -> None:
        QObject.__init__(self)
        self._state = GameSessionState.OFF
        self._rehost = False
        self.game_uid: int | None = None
        self.game_name: str | None = None
        self.game_mod: str | None = None
        self.game_visibility: str | None = None
        self.game_map: str | None = None
        self.game_password: str | None = None
        self.player_id = player_id
        self.player_login = player_login

        self._joins, self._connects = [], []

        self._process = game_process_instance
        self._process.started.connect(self._launched)
        self._process.finished.connect(self._exited)

        self.state = GameSessionState.LISTENING

        self._relay_port = 0

        self.gpg_server = GPGNetServer(player_id, player_login, logger)
        self.gpg_server.game_connected.connect(self.new_game_connection)
        self.gpg_server.game_full.connect(self.gameFullSignal.emit)
        self.gpg_server.game_launched.connect(self.game_launched.emit)

        self.ice_adapter_process = None
        self.ice_adapter_client = None
        self.ice_servers_poller = None

        self.ice_adapter_manager = IceAdapterManager(self)
        self.ice_adapter_manager.done.connect(self.on_ice_version_set)

        self.lobby_mode = LobbyInitMode.NORMAL

    def start_ice_adapter(self, init_mode: LobbyInitMode = LobbyInitMode.NORMAL) -> None:
        self.lobby_mode = init_mode
        self.ice_adapter_manager.get_releases()

    def on_ice_version_set(self) -> None:
        if self.ice_adapter_manager.adapter_kind == "java":
            self.start_java_process()
        else:
            self.start_go_process()

    def _start_ice_process(self, ice_port: int) -> None:
        assert self.game_uid is not None
        self.ice_adapter_process = IceAdapterProcess(
            player_id=self.player_id,
            player_login=self.player_login,
            game_id=self.game_uid,
            port=ice_port,
        )
        self._relay_port = self.ice_adapter_process.gpg_port()
        self.ice_adapter_process.start()

    def start_go_process(self) -> None:
        ice_port = self.gpg_server.start(self.lobby_mode)
        self._start_ice_process(ice_port)
        self.ready.emit(self._relay_port)

    def start_java_process(self) -> None:
        with tcp_server() as server:
            ice_port = server.serverPort()
        self._start_ice_process(ice_port)
        assert self.ice_adapter_process is not None
        self.ice_adapter_client = IceAdapterClient(game_session=self, logger=logger)
        self.ice_adapter_client.statusChanged.connect(self.on_ice_adapter_started)
        self.ice_adapter_client.connect_("127.0.0.1", self.ice_adapter_process.port())

    def on_ice_adapter_started(self, status: dict[str, Any]) -> None:
        logger.info(
            "ICE adapter started an listening on port %d for GPGNet connections",
            self._relay_port,
        )
        self.ice_adapter_client.statusChanged.disconnect(self.on_ice_adapter_started)
        assert self.ice_adapter_client is not None
        assert self.game_uid is not None
        self.ice_servers_poller = IceServersPoller(self.ice_adapter_client, self.game_uid)
        self.set_lobby_init_mode()
        self.ready.emit(self._relay_port)

    def close_ice_adapter(self) -> None:
        self.gpg_server.close()
        if self.ice_adapter_client:
            self.ice_adapter_client.close()
            self.ice_adapter_client = None
        if self.ice_adapter_process:
            self.ice_adapter_process.close()
            self.ice_adapter_process = None
        self._relay_port = 0

    @property
    def relay_port(self) -> int:
        return self._relay_port

    @property
    def state(self) -> GameSessionState:
        return self._state

    @state.setter
    def state(self, val: GameSessionState) -> None:
        self._state = val

    def send(self, command: str, args: list[str | int]) -> None:
        logger.info("Outgoing relay message %s %s", command, args)
        client.instance.lobby_connection.send({
            "command": command,
            "target": "game",
            "args": args or [],
        })

    def set_lobby_init_mode(self) -> None:
        if (
            not self.ice_adapter_client
            or not self.ice_adapter_client.connected
        ):
            logger.error(
                "ICE adapter client not connected when calling "
                "setLobbyInitMode",
            )
            return
        self.ice_adapter_client.call("setLobbyInitMode", [self.lobby_mode.name.lower()])

    def new_game_connection(self) -> None:
        logger.info("Game connected through GPGNet")
        self.state = GameSessionState.RUNNING

    def _launched(self) -> None:
        logger.info("Game has started")
        client.instance.lobby_reconnector.keepalive = True

    def _exited(self, code: int, status: QProcess.ExitStatus) -> None:
        self.state = GameSessionState.OFF
        logger.info("Game has exited. Status: %s. Code: %d", status, code)
        self.send('GameState', ['Ended'])
        client.instance.lobby_reconnector.keepalive = False

        if self._rehost:
            client.instance.host_game(
                title=self.game_name,
                mod=self.game_mod,
                visibility=self.game_visibility,
                mapname=self.game_map,
                password=self.game_password,
            )

        self._rehost = False
        self.game_uid = None
        self.game_name = None
        self.game_mod = None
        self.game_visibility = None
        self.game_map = None
        self.game_password = None
        self.close_ice_adapter()

    def on_game_message(self, command: str, args: list[str]) -> None:
        logger.info("Incoming GPGNet: %s %s", command, args)
        if command == "Rehost":
            self._rehost = True
        elif command == "GameFull":
            self.gameFullSignal.emit()
        elif command == "GameState" and len(args) > 0:
            if args[0] == "Launching" and self.lobby_mode is LobbyInitMode.NORMAL:
                self.game_launched.emit()
