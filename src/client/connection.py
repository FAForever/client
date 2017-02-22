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

    def __init__(self, host, port):
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

        self.dispatch = None

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
                if self.dispatch is not None:
                    self.dispatch(json.loads(action))
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


class LobbyConnection(QtCore.QObject):

    # These signals are emitted when the client is connected or disconnected from FAF
    connected = QtCore.pyqtSignal()
    disconnected = QtCore.pyqtSignal()
    state_changed = QtCore.pyqtSignal(object)

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

    def __init__(self, client, connection):
        QtCore.QObject.__init__(self)

        self._client = client
        self._connection = connection
        self._connection.dispatch = self.dispatch
        self._connection.state_changed.connect(self.on_connection_state_changed)

        self._state = ClientState.NONE
        self._receivers = {}

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value
        self.state_changed.emit(value)

    def on_connection_state_changed(self, state):
        if self.state == ClientState.SHUTDOWN:
            return

        if state == ConnectionState.CONNECTED:
            self.on_connected()
            self.state = ClientState.ACCEPTED
        elif state == ConnectionState.DISCONNECTED:
            self.on_disconnected()
            self.state = ClientState.DISCONNECTED
        elif state == ConnectionState.DROPPED:
            self.on_disconnected()
            self.state = ClientState.DROPPED
        elif state == ConnectionState.RECONNECTING:
            self.state = ClientState.RECONNECTING

    def send(self, message):
        self._connection.send(message)

    @QtCore.pyqtSlot()
    def on_connected(self):
        self._connection.send(dict(command="ask_session",
                                   version=config.VERSION,
                                   user_agent="faf-client"))
        self.connected.emit()

    def mark_for_shutdown(self):
        self.state = ClientState.SHUTDOWN

    def doLogin(self):
        self.state = ClientState.NONE

    @QtCore.pyqtSlot()
    def on_disconnected(self):
        logger.warn("Disconnected from lobby server.")

        if self.state == ClientState.ACCEPTED:
            self._client.clear_players()
        self.disconnected.emit()

    def subscribe_to(self, target, receiver):
        self._receivers[target] = receiver

    def unsubscribe(self, target, receiver):
        del self._receivers[target]

    def dispatch(self, message):
        if "command" in message:
            cmd = "handle_" + message['command']
            if "target" in message:
                receiver = self._receivers.get(message['target'])
                if hasattr(receiver, cmd):
                    getattr(receiver, cmd)(message)
                elif hasattr(receiver, 'handle_message'):
                    receiver.handle_message(message)
                else:
                    logger.warn("No receiver for message {}".format(message))
            else:
                if hasattr(self, cmd):
                    getattr(self, cmd)(message)
                else:
                    logger.error("Unknown JSON command: %s" % message['command'])
                    raise ValueError
        else:
            logger.debug("No command in message.")

    def handle_updated_achievements(self, message):
        pass

    def handle_session(self, message):
        self._client.handle_session(message)

    def handle_invalid(self, message):
        self.state = ClientState.DISCONNECTED
        raise Exception(message)

    def handle_stats(self, message):
        self.statsInfo.emit(message)

    def handle_update(self, message):
        self.state = ClientState.DISCONNECTED
        self._client.handle_update(message)

    def handle_welcome(self, message):
        self.state = ClientState.ONLINE
        self._client.handle_welcome(message)

    def handle_registration_response(self, message):
        self._client.handle_registration_response(message)

    def handle_game_launch(self, message):
        self._client.handle_game_launch(message)

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
            # sometimes we get the game_info message before a game session was created
            self._client.fill_in_session_info(message)
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

    def handle_matchmaker_info(self, message):
        self._client.handle_matchmaker_info(message)

    def handle_avatar(self, message):
        if "avatarlist" in message:
            self.avatarList.emit(message["avatarlist"])

    def handle_admin(self, message):
        if "avatarlist" in message:
            self.avatarList.emit(message["avatarlist"])

        elif "player_avatar_list" in message:
            self.playerAvatarList.emit(message)

    def handle_social(self, message):
        self._client.handle_social(message)

    def handle_player_info(self, message):
        self._client.handle_player_info(message)

    def handle_authentication_failed(self, message):
        self.state = ClientState.DISCONNECTED
        self._client.handle_authentication_failed(message)

    def handle_notice(self, message):
        self._client.handle_notice(message)
