from __future__ import annotations

import json
import logging
import os
import time
from enum import Enum
from typing import TYPE_CHECKING
from typing import Literal

import zstandard
from PyQt6 import QtCore
from PyQt6 import QtNetwork
from PyQt6 import QtWidgets
from PyQt6.QtNetwork import QAbstractSocket
from PyQt6.QtWebSockets import QWebSocket

from src import fa
from src import util
from src.api.ApiAccessors import UserApiAccessor
from src.config import Settings
from src.qt.utils import qopen

if TYPE_CHECKING:
    from src.client._clientwindow import ClientWindow


class ReplayRecorder(QtCore.QObject):
    """
    This is a simple class that establishes communication between the game
    and the replay server with its input_socket and relay_socket respectively
    It is used for:
    1. Taking the FA replay data input from input_socket and relay it to the
    replay server; save replay to a file at the end.
    2. Taking the FA replay data from relay_socket and send it to the game
    via its input_socket for live replays.
    """
    _logger = logging.getLogger(__name__)

    class Operation(Enum):
        GET = "G/"
        POST = "P/"
        UNDEFINED = ""

    def __init__(
            self,
            parent: ReplayServer,
            local_socket: QtNetwork.QTcpSocket,
    ) -> None:
        super().__init__()
        self._parent = parent
        self.operation = self.Operation.UNDEFINED
        self.input_socket = local_socket
        self.input_socket.setSocketOption(QtNetwork.QTcpSocket.SocketOption.KeepAliveOption, 1)
        self.input_socket.readyRead.connect(self.read_from_game)
        self.input_socket.disconnected.connect(self.input_disconnected)
        self._logger.info("FA connected locally.")

        # Create a file to write the replay data into
        self.replay_data = QtCore.QByteArray()
        self.replayInfo = fa.instance._info or {}

        self._host = Settings.get('replay_server/host')
        self._port = Settings.get('replay_server/port', type=int)

        self.relay_socket = QWebSocket()
        self.relay_socket.connected.connect(self.on_relay_connected)
        self.relay_socket.errorOccurred.connect(self.on_relay_error)
        self.relay_socket.binaryMessageReceived.connect(self.on_server_message)
        self.relay_socket.stateChanged.connect(self.on_relay_state_changed)

        self.api = UserApiAccessor()
        self.api.get_by_endpoint("/replay/access", self.on_replay_access_url, self.on_api_error)  # type: ignore[arg-type] # noqa: E501

        self.input_buffer = QtCore.QByteArray()

    def on_replay_access_url(self, data: dict[Literal["accessUrl"], str]) -> None:
        url = QtCore.QUrl(data["accessUrl"])
        self.relay_socket.open(url)

    def on_api_error(self, reply: QtNetwork.QNetworkReply) -> None:
        self._logger.error("Could not retrieve replay access url: %s", reply.errorString())

    def on_relay_connected(self) -> None:
        self._logger.debug(
            "internet replay server %s:%d",
            self.relay_socket.peerName(),
            self.relay_socket.peerPort(),
        )
        if not self.input_buffer.isEmpty():
            self.relay_socket.sendBinaryMessage(self.input_buffer)
            self.input_buffer.clear()

    def on_relay_error(self, error: QtNetwork.QAbstractSocket.SocketError) -> None:
        self._logger.error(
            "no connection to internet replay server: %s (%s)",
            error,
            self.relay_socket.errorString(),
        )

    def on_relay_state_changed(self, state: QAbstractSocket.SocketState) -> None:
        self._logger.debug("Connection state to replay server changed: %s", state)

    def on_server_message(self, message: QtCore.QByteArray) -> None:
        self.input_socket.write(message.data())

    def __del__(self) -> None:
        # Clean up our socket objects, in accordance to the hint from the Qt
        # docs (recommended practice)
        self._logger.debug("destructor entered")
        self.input_socket.deleteLater()
        self.relay_socket.deleteLater()

    def read_from_game(self) -> None:
        data = self.input_socket.readAll()

        # Record locally
        if self.replay_data.isEmpty():
            # This prefix means "P"osting replay in the livereplay protocol of
            # FA, this needs to be stripped from the local file
            if data.startsWith(b"P/"):
                self.operation = self.Operation.POST
                rest = data.indexOf(b"\x00") + 1
                self._logger.info("Stripping prefix '%s' from replay.", data.left(rest - 1))
                self.replay_data.append(data.right(data.size() - rest))
            elif data.startsWith(b"G/"):
                self.operation = self.Operation.GET
                self.replay_data.append(data)
            else:  # should not happen
                self._logger.warning("incorrect header from game to replayserver: %s", data)
                self.replay_data.append(data)
        else:
            self.replay_data.append(data)

        # Relay to faforever.com
        if self.relay_socket.state() is QtNetwork.QAbstractSocket.SocketState.ConnectedState:
            if not self.input_buffer.isEmpty():
                self.relay_socket.sendBinaryMessage(self.input_buffer)
                self.input_buffer.clear()
            self.relay_socket.sendBinaryMessage(data)
        else:
            self.input_buffer.append(data)

    def done(self) -> None:
        self._logger.info("closing replay file")
        self._parent.remove_recorder(self)

    @QtCore.pyqtSlot()
    def input_disconnected(self) -> None:
        self._logger.info("FA disconnected locally.")

        # Part of the hardening - ensure all buffered local replay data is read
        # and relayed
        if self.input_socket.bytesAvailable():
            self._logger.info("Relaying remaining bytes: %d", self.input_socket.bytesAvailable())
            self.read_from_game()

        # Part of the hardening - ensure successful sending of the rest of the
        # replay to the server
        if self.relay_socket.bytesToWrite():
            self._logger.info(
                "Waiting for replay transmission to finish: %s bytes",
                self.relay_socket.bytesToWrite(),
            )

            progress = QtWidgets.QProgressDialog(
                "Finishing Replay Transmission", "Cancel", 0, 0,
            )
            progress.show()

            while self.relay_socket.bytesToWrite() and progress.isVisible():
                QtWidgets.QApplication.processEvents()

            progress.close()

        self.relay_socket.close()

        if self.operation is self.Operation.POST:
            self.write_replay_file()

        self.done()

    def write_replay_file(self) -> None:
        # Update info block if possible.
        if (
            fa.instance._info
            and fa.instance._info['uid'] == self.replayInfo['uid']
        ):
            if fa.instance._info.setdefault('complete', False):
                self._logger.info("Found Complete Replay Info")
            else:
                self._logger.warning("Replay Info not Complete")

            self.replayInfo: dict[str, str | float] = fa.instance._info

        self.replayInfo['game_end'] = time.time()
        self.replayInfo["compression"] = "zstd"
        self.replayInfo["version"] = 2

        basename = "{}-{}.fafreplay".format(
            self.replayInfo['uid'], self.replayInfo['recorder'],
        )
        filename = os.path.join(util.REPLAY_DIR, basename)
        self._logger.info(
            "Writing local replay as %s, containing %d bytes of replay data.",
            filename, self.replay_data.size(),
        )

        with qopen(filename, QtCore.QFile.OpenModeFlag.WriteOnly) as replay:
            replay.write(json.dumps(self.replayInfo).encode() + b"\n")
            compressor = zstandard.ZstdCompressor()
            with compressor.stream_writer(replay) as writer:  # type: ignore[arg-type]
                writer.write(self.replay_data.data())


class ReplayServer(QtNetwork.QTcpServer):
    """
    This is a local listening server that FA can send its replay data to.
    It will instantiate a fresh ReplayRecorder for each FA instance that
    launches.
    """
    _logger = logging.getLogger(__name__)

    def __init__(self, client: ClientWindow) -> None:
        super().__init__()
        self.recorders: list[ReplayRecorder] = []
        self.client = client
        self._logger.debug("initializing...")
        self.newConnection.connect(self.accept_connection)

    def doListen(self) -> bool:
        while not self.isListening():
            self.listen(QtNetwork.QHostAddress.SpecialAddress.LocalHost)
            if self.isListening():
                self._logger.info(
                    "listening on address %s:%d",
                    self.serverAddress().toString(),
                    self.serverPort(),
                )
            else:
                self._logger.error(
                    "cannot listen, port probably used by another application: %d",
                    self.serverPort(),
                )
                answer = QtWidgets.QMessageBox.warning(
                    None,
                    "Port Occupied",
                    (
                        "FAF couldn't start its local replay server, which is "
                        "needed to play Forged Alliance online. Possible "
                        "reasons: <ul><li><b>FAF is already running</b> (most "
                        "likely)</li><li>another program is listening on port "
                        "{}</li></ul>".format(self.serverPort())
                    ),
                    QtWidgets.QMessageBox.StandardButton.Retry,
                    QtWidgets.QMessageBox.StandardButton.Abort,
                )
                if answer == QtWidgets.QMessageBox.StandardButton.Abort:
                    return False
        return True

    def remove_recorder(self, recorder: ReplayRecorder) -> None:
        if recorder in self.recorders:
            self.recorders.remove(recorder)

    @QtCore.pyqtSlot()
    def accept_connection(self) -> None:
        socket = self.nextPendingConnection()
        if socket is None:
            self._logger.warning("error accepting connection: no pending connections")
            return
        self._logger.debug("incoming connection...")
        self.recorders.append(ReplayRecorder(self, socket))
