from __future__ import annotations

import logging
import time

from irc.client import Reactor
from irc.client import ServerConnectionError
from PyQt6.QtCore import QEventLoop
from PyQt6.QtCore import QObject
from PyQt6.QtCore import QUrl
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtNetwork import QAbstractSocket
from PyQt6.QtNetwork import QNetworkRequest
from PyQt6.QtWebSockets import QWebSocket

logger = logging.getLogger(__name__)


class WebSocketToSocket(QObject):
    """ Allows to use QWebSocket as a 'socket' """

    message_received = pyqtSignal()
    error_occurred = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.socket = QWebSocket()
        self.socket.binaryMessageReceived.connect(self.on_bin_message_received)
        self.socket.errorOccurred.connect(self.on_socket_error)
        self.socket.stateChanged.connect(self.on_socket_state_changed)
        self.buffer = b""

        self._connect_loop = QEventLoop()
        self.socket.connected.connect(self._connect_loop.exit)
        self.socket.errorOccurred.connect(self._connect_loop.exit)

        self._close_intended = False

    def on_socket_error(self, error: QAbstractSocket.SocketError) -> None:
        logger.error("SocketAdapter error: %s. Details: %s", error, self.socket.errorString())

    def on_socket_state_changed(self, state: QAbstractSocket.SocketState) -> None:
        logger.debug("SocketAdapter state changed: %s", state)
        # socket state can change without errors, that's why we emit `error_occurred` signal
        # here and not in the `on_socket_error` method
        if state == QAbstractSocket.SocketState.UnconnectedState and not self._close_intended:
            self.error_occurred.emit()

    def on_bin_message_received(self, message: bytes) -> None:
        # according to https://ircv3.net/specs/extensions/websocket
        # messages MUST NOT include trailing \r\n, but our non-websocket
        # library (irc) requires them
        self.buffer += message + b"\r\n"
        self.message_received.emit()

    def read(self, size: int) -> bytes:
        if self.socket.state() != QAbstractSocket.SocketState.ConnectedState:
            raise OSError
        ans, self.buffer = self.buffer[:size], self.buffer[size:]
        return ans

    def recv(self, size: int) -> bytes:
        """ Alias for read, just in case """
        return self.read(size)

    def shutdown(self, how: int) -> None:
        self.socket.deleteLater()

    def write(self, message: bytes) -> None:
        sent = self.socket.sendBinaryMessage(message.strip())
        if sent == 0:
            raise OSError

    def send(self, message: bytes) -> None:
        """ Alias for write, just in case """
        self.write(message)

    def _prepare_request(self, server_address: tuple[str, int]) -> QNetworkRequest:
        host, port = server_address
        request = QNetworkRequest()
        request.setUrl(QUrl(f"wss://{host}:{port}"))
        request.setRawHeader(b"Sec-WebSocket-Protocol", b"binary.ircv3.net")
        return request

    def connect(self, server_address: tuple[str, int]) -> None:
        self.socket.open(self._prepare_request(server_address))

        # UnknownSocketError is the default and here means "No Error"
        if self.socket.error() != QAbstractSocket.SocketError.UnknownSocketError:
            raise ServerConnectionError(self.socket.errorString())

        if self.socket.state != QAbstractSocket.SocketState.ConnectedState:
            self._connect_loop.exec()

    def close(self) -> None:
        self._close_intended = True
        self.socket.close()


class ReactorForSocketAdapter(Reactor, QObject):
    socket_error = pyqtSignal()

    def __init__(self) -> None:
        QObject.__init__(self)
        Reactor.__init__(self)
        self._on_connect = self.on_connect

    def process_once(self, timeout: float = 0.01) -> None:
        if self.sockets:
            self.process_data(self.sockets)
        else:
            time.sleep(timeout)
        self.process_timeout()

    def on_connect(self, socket: WebSocketToSocket) -> None:
        socket.message_received.connect(self.process_once)
        socket.error_occurred.connect(self.on_socket_error)

    def on_socket_error(self) -> None:
        self.socket_error.emit()


class ConnectionFactory:
    def connect(self, server_address: tuple[str, int]) -> WebSocketToSocket:
        sock = WebSocketToSocket()
        sock.connect(server_address)
        return sock

    __call__ = connect
