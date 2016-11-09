from PyQt5.QtCore import pyqtSignal
from decorators import with_logger
from connectivity.JsonRpcTcpClient import JsonRpcTcpClient

@with_logger
class IceAdapterClient(JsonRpcTcpClient):

    statusChanged = pyqtSignal(dict)

    def __init__(self, game_session):
        JsonRpcTcpClient.__init__(self, request_handler_instance=self)
        self.connected = False
        self.game_session = game_session
        self.socket.connected.connect(self.onSocketConnected)

    def onIceMsg(self, localId, remoteId, iceMsg):
        self._logger.debug("onIceMsg {} {} {}".format(localId, remoteId, iceMsg))
        self.game_session.send("IceMsg", [remoteId, iceMsg])

    def onConnectionStateChanged(self, newState):
        self._logger.debug("onConnectionStateChanged {}".format(newState))
        if self.game_session and newState == "Connected":
            self.game_session._new_game_connection()
        self.call("status", callback_result=self.onStatus)

    def onGpgNetMessageReceived(self, header, chunks):
        self._logger.debug("onGpgNetMessageReceived {} {}".format(header, chunks))
        self.game_session._on_game_message(header, chunks)
        #self.call("status", callback_result=self.onStatus)

    def onIceConnectionStateChanged(self, *unused):
        self.call("status", callback_result=self.onStatus)

    def onSocketConnected(self):
        self._logger.debug("connected to ice-adapter")
        self.connected = True
        self.call("status", callback_result=self.onStatus)

    def onConnected(self, localId, remoteId, connected):
        if connected:
            self._logger.debug("ice-adapter connected to player %i" % remoteId)
        else:
            self._logger.debug("ice-adapter disconnected from player %i" % remoteId)
        self.call("status", callback_result=self.onStatus)

    def onStatus(self, status):
        self.statusChanged.emit(status)