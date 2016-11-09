from decorators import with_logger

from connectivity.JsonRpcTcpClient import JsonRpcTcpClient

@with_logger
class IceAdapterClient(JsonRpcTcpClient):
    def __init__(self, game_session, port=7236):
        JsonRpcTcpClient.__init__(self, "127.0.0.1", port, self)
        self.game_session = game_session

    def onNeedSdp(self, localId, remoteId):
        self._logger.info("onNeedSdp {} {}".format(localId, remoteId))

    def onSdpGathered(self, localId, remoteId, sdp):
        self._logger.info("onSdpGathered {} {} {}".format(localId, remoteId, sdp))
        self.game_session.send("SdpRecord", [remoteId, sdp])

    def onConnectionStateChanged(self, newState):
        self._logger.info("onConnectionStateChanged {}".format(newState))
        if self.game_session and newState == "Connected":
            self.game_session._new_game_connection()

    def onGpgNetMessageReceived(self, header, chunks):
        self._logger.info("onGpgNetMessageReceived {} {}".format(header, chunks))
        self.game_session._on_game_message(header, chunks)