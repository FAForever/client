from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING
from typing import Any

from PyQt6.QtCore import pyqtSignal

from src import client
from src.client.connection import ConnectionState
from src.connectivity.JsonRpcTcpClient import JsonRpcTcpClient
from src.protocol.lobbyprotocol import GPGCommand

if TYPE_CHECKING:
    from src.fa.game_session import GameSession


class IceAdapterClient(JsonRpcTcpClient):

    statusChanged = pyqtSignal(dict)
    gpgnetmessageReceived = pyqtSignal(str, list)

    def __init__(self, game_session: GameSession, logger: logging.Logger) -> None:
        super().__init__(logger)
        self.connected = False
        self.game_session = game_session
        self.socket.connected.connect(self.onSocketConnected)
        self.iceMsgCache: list[tuple[int, Any]] = []
        client.instance.lobby_connection.connected.connect(self.onLobbyConnected)
        client.instance.lobby_dispatch.subscribe_to("game", self.handle_message)

    def onIceMsg(self, localId: int, remoteId: int, iceMsg: Any) -> None:
        self._logger.debug("onIceMsg %s %s %s", localId, remoteId, iceMsg)
        if client.instance.lobby_connection.state == ConnectionState.CONNECTED:
            self.send("IceMsg", [remoteId, iceMsg])
        elif isinstance(iceMsg, dict) and "type" in iceMsg:
            if iceMsg["type"] != "candidate":
                self.iceMsgCache.clear()
            self.iceMsgCache.append((remoteId, iceMsg))
            self._logger.debug("lobby disconnected, caching ICE message %d", len(self.iceMsgCache))

    def onConnectionStateChanged(self, newState: str) -> None:
        self._logger.debug("onConnectionStateChanged %s", newState)
        if newState == "Connected":
            self.game_session.new_game_connection()
        self.call("status", callback_result=self.onStatus)

    def onGpgNetMessageReceived(self, header: str, chunks: list[str]) -> None:
        self._logger.debug("onGpgNetMessageReceived %s %s", header, chunks)
        self.game_session.on_game_message(header, chunks)
        self.send(header, chunks)
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

    def handle_message(self, message: GPGCommand) -> None:
        command, args = message.get('command'), message.get('args', [])
        if command == 'SendNatPacket':
            # we ignore that for now with the ICE Adapter
            pass
        elif command == 'CreatePermission':
            # we ignore that for now with the ICE Adapter
            pass
        elif command == 'JoinGame':
            login, peer_id = args
            self.call("joinGame", [login, peer_id])
        elif command == 'HostGame':
            self.call("hostGame", [args[0]])
        elif command == 'ConnectToPeer':
            login, peer_id, offer = args
            self.call(
                "connectToPeer", [login, peer_id, offer],
            )
        elif command == 'DisconnectFromPeer':
            self.call("disconnectFromPeer", [args[0]])
        elif command == "IceMsg":
            peer_id, ice_msg = args
            self.call("iceMsg", [peer_id, ice_msg])
        else:
            self._logger.warning("sending unhandled GPGNet message %s %s", command, args)
            self.call("sendToGpgNet", [command, args])

    def send(self, command_id: str, args: list[Any]) -> None:
        self._logger.info("Outgoing relay message %s %s", command_id, args)
        client.instance.lobby_connection.send({
            "command": command_id,
            "target": "game",
            "args": args or [],
        })

    def close(self) -> None:
        try:
            self.call("quit", blocking=True)
        except RuntimeError:
            self._logger.warning("Could not send 'quit' command. Adapter is probably closed.")
        client.instance.lobby_dispatch.unsubscribe("game")
        super().close()
