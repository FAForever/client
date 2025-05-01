import json

from PyQt6.QtCore import pyqtSignal

from src import client
from src.client.connection import ConnectionState
from src.connectivity.JsonRpcTcpClient import JsonRpcTcpClient
from src.decorators import with_logger


@with_logger
class IceAdapterClient(JsonRpcTcpClient):

    statusChanged = pyqtSignal(dict)
    gpgnetmessageReceived = pyqtSignal(str, list)

    def __init__(self, game_session):
        JsonRpcTcpClient.__init__(self, request_handler_instance=self)
        self.connected = False
        self.game_session = game_session
        self.socket.connected.connect(self.onSocketConnected)
        self.iceMsgCache = []
        client.instance.lobby_connection.connected.connect(
            self.onLobbyConnected,
        )

    def onIceMsg(self, localId, remoteId, iceMsg):
        self._logger.debug("onIceMsg %s %s %s", localId, remoteId, iceMsg)
        if client.instance.lobby_connection.state == ConnectionState.CONNECTED:
            self.game_session.send("IceMsg", [remoteId, iceMsg])
        elif isinstance(iceMsg, dict) and "type" in iceMsg:
            if iceMsg["type"] != "candidate":
                self.iceMsgCache.clear()
            self.iceMsgCache.append((remoteId, iceMsg))
            self._logger.debug("lobby disconnected, caching ICE message %d", len(self.iceMsgCache))

    def onConnectionStateChanged(self, newState):
        self._logger.debug("onConnectionStateChanged %s", newState)
        if self.game_session and newState == "Connected":
            self.game_session._new_game_connection()
        self.call("status", callback_result=self.onStatus)

    def onGpgNetMessageReceived(self, header, chunks):
        self._logger.debug("onGpgNetMessageReceived %s %s", header, chunks)
        self.game_session._on_game_message(header, chunks)
        self.gpgnetmessageReceived.emit(header, chunks)

    def onIceConnectionStateChanged(self, *unused):
        self.call("status", callback_result=self.onStatus)

    def onSocketConnected(self):
        self._logger.debug("connected to ice-adapter")
        self.connected = True
        self.call("status", callback_result=self.onStatus)

    def onConnected(self, localId, remoteId, connected):
        if connected:
            self._logger.debug("ice-adapter connected to player %s", remoteId)
        else:
            self._logger.debug("ice-adapter disconnected from player %s", remoteId)
        self.call("status", callback_result=self.onStatus)

    def onStatus(self, status):
        if isinstance(status, str):
            status = json.loads(status)
        if "gpgpnet" in status:  # issue in current java-ice-adapter
            status["gpgnet"] = status["gpgpnet"]
        self.statusChanged.emit(status)

    def onLobbyConnected(self):
        if len(self.iceMsgCache) > 0:
            self._logger.debug("sending %d cached ICE messages", len(self.iceMsgCache))
        for remoteId, iceMsg in self.iceMsgCache:
            self.game_session.send("IceMsg", [remoteId, iceMsg])
        self.iceMsgCache.clear()
