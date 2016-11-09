from PyQt4.QtCore import pyqtSignal
from decorators import with_logger
from connectivity.JsonRpcTcpClient import JsonRpcTcpClient

@with_logger
class IceAdapterClient(JsonRpcTcpClient):

    statusChanged = pyqtSignal(dict)

    def __init__(self, game_session):
        JsonRpcTcpClient.__init__(self, request_handler_instance=self)
        self.game_session = game_session
        self.socket.connected.connect(self.onConnected)

    def onIceMsg(self, localId, remoteId, iceMsg):
        self._logger.info("onIceMsg {} {} {}".format(localId, remoteId, iceMsg))
        self.game_session.send("IceMsg", [remoteId, iceMsg])

    def onConnectionStateChanged(self, newState):
        self._logger.info("onConnectionStateChanged {}".format(newState))
        if self.game_session and newState == "Connected":
            self.game_session._new_game_connection()
        self.call("status", callback_result=self.onStatus)

    def onGpgNetMessageReceived(self, header, chunks):
        self._logger.info("onGpgNetMessageReceived {} {}".format(header, chunks))
        self.game_session._on_game_message(header, chunks)
        #self.call("status", callback_result=self.onStatus)

    def onIceConnectionStateChanged(self, *unused):
        self.call("status", callback_result=self.onStatus)

    def onDatachannelOpen(self, *unused):
        self.call("status", callback_result=self.onStatus)

    def onConnected(self):
        self._logger.info("connected to ICE adapter")
        self.call("status", callback_result=self.onStatus)

    def onStatus(self, status):
        #self._logger.info("onStatus {}".format(status))
        self.statusChanged.emit(status)