from PyQt5 import QtCore, QtNetwork
import json

import logging
logger = logging.getLogger(__name__)

# Connection to the replay vault. Given how this works, it will one day
# be replaced with FAF API.


class ReplaysConnection(QtCore.QObject):
    def __init__(self, dispatch, host, port):
        QtCore.QObject.__init__(self)

        self.dispatch = dispatch
        self.blockSize = 0
        self.host = host
        self.port = port

        self.replayVaultSocket = QtNetwork.QTcpSocket()
        self.replayVaultSocket.readyRead.connect(self._readDataFromServer)
        self.replayVaultSocket.error.connect(self._handleServerError)
        self.replayVaultSocket.disconnected.connect(self._disconnected)

    def connect_(self):
        """ connect to the replay vault server """
        state = self.replayVaultSocket.state()
        states = QtNetwork.QAbstractSocket
        if state != states.ConnectedState and state != states.ConnectingState:
            self.replayVaultSocket.connectToHost(self.host, self.port)

    def receiveJSON(self, data_string, stream):
        """ A fairly pythonic way to process received strings as JSON messages. """

        try:
            message = json.loads(data_string)
            self.dispatch.dispatch(message)
        except ValueError as e:
            logger.error("Error decoding json ")
            logger.error(e)
        self.replayVaultSocket.disconnectFromHost()

    @QtCore.pyqtSlot()
    def _readDataFromServer(self):
        ins = QtCore.QDataStream(self.replayVaultSocket)
        ins.setVersion(QtCore.QDataStream.Qt_4_2)

        while not ins.atEnd():
            if self.blockSize == 0:
                if self.replayVaultSocket.bytesAvailable() < 4:
                    return
                self.blockSize = ins.readUInt32()
            if self.replayVaultSocket.bytesAvailable() < self.blockSize:
                return

            action = ins.readQString()
            logger.debug("Replay Vault Server: " + action)
            self.receiveJSON(action, ins)
            self.blockSize = 0

    def send(self, message):
        data = json.dumps(message)
        logger.debug("Outgoing JSON Message: " + data)
        self._writeToServer(data)

    def _writeToServer(self, action, *args, **kw):
        logger.debug(("writeToServer(" + action + ", [" + ', '.join(args) + "])"))

        block = QtCore.QByteArray()
        out = QtCore.QDataStream(block, QtCore.QIODevice.ReadWrite)
        out.setVersion(QtCore.QDataStream.Qt_4_2)
        out.writeUInt32(0)
        out.writeQString(action)

        for arg in args:
            if type(arg) is int:
                out.writeInt(arg)
            elif isinstance(arg, str):
                out.writeQString(arg)
            elif type(arg) is float:
                out.writeFloat(arg)
            elif type(arg) is list:
                out.writeQVariantList(arg)
            else:
                logger.warning("Uninterpreted Data Type: " + str(type(arg)) + " of value: " + str(arg))
                out.writeQString(str(arg))

        out.device().seek(0)
        out.writeUInt32(block.size() - 4)
        self.replayVaultSocket.write(block)

    def _handleServerError(self, socketError):
        if socketError == QtNetwork.QAbstractSocket.RemoteHostClosedError:
            logger.info("Replay Server down: The server is down for maintenance, please try later.")

        elif socketError == QtNetwork.QAbstractSocket.HostNotFoundError:
            logger.info("Connection to Host lost. Please check the host name and port settings.")

        elif socketError == QtNetwork.QAbstractSocket.ConnectionRefusedError:
            logger.info("The connection was refused by the peer.")
        else:
            logger.info("The following error occurred: %s." % self.replayVaultSocket.errorString())

    def _disconnected(self):
        logger.debug("Disconnected from server")
