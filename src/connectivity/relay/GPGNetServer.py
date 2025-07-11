import logging
from typing import cast

from PyQt6.QtCore import QByteArray
from PyQt6.QtCore import QDataStream
from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtNetwork import QHostAddress
from PyQt6.QtNetwork import QTcpServer
from PyQt6.QtNetwork import QTcpSocket

from src import client
from src.connectivity.relay.GPGProtocol import ConnectToPeer
from src.connectivity.relay.GPGProtocol import CreateLobby
from src.connectivity.relay.GPGProtocol import DisconnectFromPeer
from src.connectivity.relay.GPGProtocol import GameEnded
from src.connectivity.relay.GPGProtocol import GameFull
from src.connectivity.relay.GPGProtocol import GameState
from src.connectivity.relay.GPGProtocol import GameStateMessage
from src.connectivity.relay.GPGProtocol import Generic
from src.connectivity.relay.GPGProtocol import GPGFieldType
from src.connectivity.relay.GPGProtocol import GPGMessage
from src.connectivity.relay.GPGProtocol import HostGame
from src.connectivity.relay.GPGProtocol import JoinGame
from src.connectivity.relay.GPGProtocol import LobbyInitMode
from src.protocol.lobbyprotocol import GPGCommand


class BufferDataSream(QDataStream):
    def __init__(self, open_mode: QDataStream.OpenModeFlag) -> None:
        self._buffer = QByteArray()
        super().__init__(self._buffer, open_mode)
        dev = self.device()
        assert dev is not None
        self._device = dev

    def reset(self) -> None:
        self._buffer.clear()
        self._device.reset()

    def append(self, data: QByteArray) -> None:
        self._buffer.append(data)

    def data(self) -> bytes:
        return self._buffer.data()


class GPGNetServer(QObject):
    game_connected = pyqtSignal()
    game_full = pyqtSignal()
    game_launched = pyqtSignal()

    def __init__(
        self,
        player_id: int,
        player_login: str,
        logger: logging.Logger,
        lobby_mode: LobbyInitMode = LobbyInitMode.NORMAL,
    ) -> None:
        super().__init__()
        self.player_id = player_id
        self.player_login = player_login
        self.logger = logger
        self.lobby_mode = lobby_mode

        self.server = QTcpServer()
        self.server.pendingConnectionAvailable.connect(self.on_pending_connection)
        # FIXME: this whole chain of signal propagation looks weird?
        self.server.pendingConnectionAvailable.connect(self.game_connected.emit)

        self.socket: QTcpSocket | None = None

        self.read_stream = BufferDataSream(QDataStream.OpenModeFlag.ReadWrite)
        self.write_stream = BufferDataSream(QDataStream.OpenModeFlag.WriteOnly)
        self.read_stream.setByteOrder(QDataStream.ByteOrder.LittleEndian)
        self.write_stream.setByteOrder(QDataStream.ByteOrder.LittleEndian)

        self.player_id = player_id
        self.player_login = player_login

    def on_socket_data(self) -> None:
        assert self.socket is not None
        if self.socket.bytesAvailable() == 0:
            return
        self.read_stream.append(self.socket.readAll())
        for message in self.decode_gpg_commands():
            self.process_gpg_message(message)

    def on_socket_error(self, error: QTcpSocket.SocketError) -> None:
        if self.socket is None:
            self.logger.error("GPG socket error when there is no socket!?")
        else:
            self.logger.error("GPG socket error %s: %s", error, self.socket.errorString())

    def create_message(self, command: str, args: list[str | int]) -> GPGMessage:
        match command:
            case "GameState":
                return GameStateMessage(GameState(cast(str, args[0])))
            case "GameFull":
                return GameFull()
            case "GameEnded":
                return GameEnded()
            case "CreateLobby":
                return CreateLobby(
                    LobbyInitMode(cast(int, args[0])),
                    cast(int, args[1]),
                    cast(str, args[2]),
                    cast(int, args[3]),
                )
            case _:
                return Generic(command, args)

    def read_string(self) -> str:
        size = self.read_stream.readInt()
        return self.read_stream.readRawData(size).decode()

    def read_arguments(self) -> list[str | int]:
        args: list[str | int] = []
        for _ in range(self.read_stream.readInt()):
            arg_type = GPGFieldType(self.read_stream.readUInt8())
            match arg_type:
                case GPGFieldType.INT:
                    args.append(self.read_stream.readInt())
                case GPGFieldType.STRING:
                    args.append(self.read_string())
        return args

    def decode_gpg_commands(self) -> list[GPGMessage]:
        messages: list[GPGMessage] = []
        while not self.read_stream.atEnd():
            command = self.read_string()
            args = self.read_arguments()
            messages.append(self.create_message(command, args))
        self.read_stream.reset()
        return messages

    def process_gpg_message(self, message: GPGMessage) -> None:
        self.logger.info("Incoming GPGNet: %s", message)
        match message:
            case GameStateMessage(GameState.IDLE):
                make_lobby = CreateLobby(self.lobby_mode, 0, self.player_login, self.player_id)
                self.send_gpg_message(make_lobby)
            case GameStateMessage(GameState.LAUNCHING):
                if self.lobby_mode is LobbyInitMode.NORMAL:
                    self.game_launched.emit()
            case GameFull():
                self.game_full.emit()
            case _:
                ...
        client.instance.lobby_connection.send({
            "command": message.command(),
            "target": "game",
            "args": message.arguments() or [],
        })

    def handle_message(self, message: GPGCommand) -> None:
        command, args = message.get("command"), message.get("args", [])
        match command:
            case "JoinGame":
                gpg_message = JoinGame(cast(str, args[0]), cast(int, args[1]))
            case "HostGame":
                gpg_message = HostGame(cast(str, args[0]))
            case "ConnectToPeer":
                login, peer_id, _ = args
                gpg_message = ConnectToPeer(cast(str, login), cast(int, peer_id))
            case "DisconnectFromPeer":
                gpg_message = DisconnectFromPeer(cast(int, args[0]))
            case unhandled:
                self.logger.info("GPG command not handled: %s", unhandled)
                return
        self.send_gpg_message(gpg_message)

    def write_string(self, string: str) -> None:
        self.write_stream.writeBytes(string.encode())

    def write_arguments(self, args: list[str | int]) -> None:
        self.write_stream.writeInt(len(args))
        for arg in args:
            if isinstance(arg, int):
                self.write_stream.writeUInt8(0)
                self.write_stream.writeInt(arg)
            else:
                self.write_stream.writeUInt8(1)
                self.write_string(arg)

    def send_gpg_message(self, message: GPGMessage) -> None:
        self.write_string(message.command())
        self.write_arguments(message.arguments())
        assert self.socket is not None
        self.socket.write(self.write_stream.data())
        self.write_stream.reset()

    def start(self, lobby_init_mode: LobbyInitMode) -> int:
        self.server.listen(QHostAddress.SpecialAddress.LocalHost)
        self.lobby_mode = lobby_init_mode
        return self.server.serverPort()

    def on_pending_connection(self) -> None:
        if (socket := self.server.nextPendingConnection()) is None:
            return
        self.socket = socket
        self.socket.readyRead.connect(self.on_socket_data)
        self.socket.errorOccurred.connect(self.on_socket_error)
        client.instance.lobby_dispatch.subscribe_to("game", self.handle_message)

    def close(self) -> None:
        if self.socket is not None:
            self.socket.close()
        self.server.close()
