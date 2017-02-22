from PyQt4 import QtCore, QtNetwork

import logging
import config
import fa
import json
import sys

from enum import IntEnum
from client import ClientState, LOBBY_HOST, \
    LOBBY_PORT

logger = logging.getLogger(__name__)

class ConnectionState(IntEnum):
    INITIAL = -1
    DISCONNECTED = 0
    RECONNECTING = 1
    # On this state automatically try and reconnect
    DROPPED = 2
    CONNECTED = 3

class ServerConnection(QtCore.QObject):

    # These signals are emitted when the client is connected or disconnected from FAF
    state_changed = QtCore.pyqtSignal(object)
    connected = QtCore.pyqtSignal()
    disconnected = QtCore.pyqtSignal()

    def __init__(self, host, port, dispatch):
        QtCore.QObject.__init__(self)
        self.socket = QtNetwork.QTcpSocket()
        self.socket.readyRead.connect(self.readFromServer)
        self.socket.disconnected.connect(self.disconnectedFromServer)
        self.socket.error.connect(self.socketError)
        self.socket.connected.connect(self.on_connected)
        self.socket.setSocketOption(QtNetwork.QTcpSocket.KeepAliveOption, 1)

        self._host = host
        self._port = port
        self._state = ConnectionState.INITIAL
        self.blockSize = 0
        self._connection_attempts = 0
        self._disconnect_requested = False
        self.localIP = None

        self._dispatch = dispatch

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value
        self.state_changed.emit(value)

    def doConnect(self):
        self._disconnect_requested = False
        self.socket.connectToHost(self._host, self._port)

    @QtCore.pyqtSlot()
    def on_connected(self):
        self.state = ConnectionState.CONNECTED
        self._connection_attempts = 0
        self.localIP = self.socket.localAddress()
        self.connected.emit()

    def reconnect(self):
        """
        Reconnect to the server
        :return:
        """
        self._disconnect_requested = False
        self._connection_attempts += 1
        self.state = ConnectionState.RECONNECTING
        self.socket.connectToHost(self._host, self._port)

    def socket_connected(self):
        return self.socket.state() == QtNetwork.QTcpSocket.ConnectedState

    def disconnect(self):
        self._disconnect_requested = True
        self.socket.disconnectFromHost()

    def set_upnp(self, port):
        fa.upnp.createPortMapping(self.socket.localAddress().toString(), port, "UDP")

    @QtCore.pyqtSlot()
    def readFromServer(self):
        ins = QtCore.QDataStream(self.socket)
        ins.setVersion(QtCore.QDataStream.Qt_4_2)

        while ins.atEnd() == False:
            if self.blockSize == 0:
                if self.socket.bytesAvailable() < 4:
                    return
                self.blockSize = ins.readUInt32()
            if self.socket.bytesAvailable() < self.blockSize:
                return

            action = ins.readQString()
            logger.debug("Server: '%s'" % action)

            if action == "PING":
                self.writeToServer("PONG")
                self.blockSize = 0
                return
            try:
                self._dispatch(json.loads(action))
            except:
                logger.error("Error dispatching JSON: " + action, exc_info=sys.exc_info())

            self.blockSize = 0

    def writeToServer(self, action, *args, **kw):
        """
        Writes data to the deprecated stream API. Do not use.
        """
        logger.debug("Client: " + action)

        block = QtCore.QByteArray()
        out = QtCore.QDataStream(block, QtCore.QIODevice.ReadWrite)
        out.setVersion(QtCore.QDataStream.Qt_4_2)

        out.writeUInt32(2 * len(action) + 4)
        out.writeQString(action)

        self.socket.write(block)

    def send(self, message):
        data = json.dumps(message)
        if message.get('command') == 'hello':
            logger.info('Logging in with {}'.format({
                                                        k: v for k, v in message.items() if k != 'password'
                                                        }))
        else:
            logger.info("Outgoing JSON Message: " + data)

        self.writeToServer(data)


    @QtCore.pyqtSlot()
    def disconnectedFromServer(self):
        logger.warn("Disconnected from lobby server.")
        self.blockSize = 0
        self.disconnected.emit()
        if self._disconnect_requested:
            self.state = ConnectionState.DISCONNECTED
        if self.state == ConnectionState.DISCONNECTED:
            return

        self.state = ConnectionState.DROPPED
        if self._connection_attempts < 2:
            logger.info("Reconnecting immediately")
            self.reconnect()
        else:
            timer = QtCore.QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(self.reconnect)
            t = self._connection_attempts * 10000
            timer.start(t)
            logger.info("Scheduling reconnect in {}".format(t / 1000))

    @QtCore.pyqtSlot(QtNetwork.QAbstractSocket.SocketError)
    def socketError(self, error):
        if (error == QtNetwork.QAbstractSocket.SocketTimeoutError
                or error == QtNetwork.QAbstractSocket.NetworkError
                or error == QtNetwork.QAbstractSocket.ConnectionRefusedError
                or error == QtNetwork.QAbstractSocket.RemoteHostClosedError):
            logger.info("Timeout/network error: {}".format(self.socket.errorString()))
        else:
            logger.error("Fatal TCP Socket Error: " + self.socket.errorString())
        self.socket.disconnectFromHost()


class Dispatcher():
    def __init__(self):
        self._receivers = {}
        self._dispatchees = {}

    def __setitem__(self, key, fn):
        self._dispatchees[key] = fn

    def __delitem__(self, key):
        del self._dispatchees[key]

    def subscribe_to(self, target, fn, msg = None):
        self._receivers[(target, msg)] = fn

    def unsubscribe(self, target, msg = None):
        del self._receivers[(target, msg)]

    def dispatch(self, message):
        if "command" not in message:
            logger.debug("No command in message.")
            return

        cmd = message['command']
        if "target" in message:
            fn = self._receivers.get((message['target'], cmd))
            fn = self._receivers.get((message['target'], None)) if fn is None else fn
            if fn is not None:
                fn(message)
            else:
                logger.warn("No receiver for message {}".format(message))
        else:
            fn = self._dispatchees.get(cmd)
            if fn is not None:
                fn(message)
            else:
                logger.error("Unknown JSON command: %s" % message['command'])
                raise ValueError


class LobbyInfo(QtCore.QObject):

    # These signals propagate important client state changes to other modules
    gameInfo = QtCore.pyqtSignal(dict)
    statsInfo = QtCore.pyqtSignal(dict)
    coopInfo = QtCore.pyqtSignal(dict)
    tutorialsInfo = QtCore.pyqtSignal(dict)
    modInfo = QtCore.pyqtSignal(dict)
    modVaultInfo = QtCore.pyqtSignal(dict)
    replayVault = QtCore.pyqtSignal(dict)
    coopLeaderBoard = QtCore.pyqtSignal(dict)
    avatarList = QtCore.pyqtSignal(list)
    playerAvatarList = QtCore.pyqtSignal(dict)

    def __init__(self, dispatcher):
        QtCore.QObject.__init__(self)

        self._dispatcher = dispatcher
        self._dispatcher["updated_achievements"] = self.handle_updated_achievements
        self._dispatcher["stats"] = self.handle_stats
        self._dispatcher["coop_info"] = self.handle_coop_info
        self._dispatcher["tutorials_info"] = self.handle_tutorials_info
        self._dispatcher["mod_info"] = self.handle_mod_info
        self._dispatcher["game_info"] = self.handle_game_info
        self._dispatcher["modvault_list_info"] = self.handle_modvault_list_info
        self._dispatcher["modvault_info"] = self.handle_modvault_info
        self._dispatcher["replay_vault"] = self.handle_replay_vault
        self._dispatcher["coop_leaderboard"] = self.handle_coop_leaderboard
        self._dispatcher["avatar"] = self.handle_avatar
        self._dispatcher["admin"] = self.handle_admin

    def handle_updated_achievements(self, message):
        pass

    def handle_stats(self, message):
        self.statsInfo.emit(message)

    def handle_coop_info(self, message):
        self.coopInfo.emit(message)

    def handle_tutorials_info(self, message):
        self.tutorialsInfo.emit(message)

    def handle_mod_info(self, message):
        self.modInfo.emit(message)

    def handle_game_info(self, message):
        if 'games' in message:
            for game in message['games']:
                self.gameInfo.emit(game)
        else:
            self.gameInfo.emit(message)

    def handle_modvault_list_info(self, message):
        modList = message["modList"]
        for mod in modList:
            self.handle_modvault_info(mod)

    def handle_modvault_info(self, message):
        self.modVaultInfo.emit(message)

    def handle_replay_vault(self, message):
        self.replayVault.emit(message)

    def handle_coop_leaderboard(self, message):
        self.coopLeaderBoard.emit(message)

    def handle_avatar(self, message):
        if "avatarlist" in message:
            self.avatarList.emit(message["avatarlist"])

    def handle_admin(self, message):
        if "avatarlist" in message:
            self.avatarList.emit(message["avatarlist"])

        elif "player_avatar_list" in message:
            self.playerAvatarList.emit(message)
