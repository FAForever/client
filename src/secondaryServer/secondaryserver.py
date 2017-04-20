from PyQt4 import QtCore, QtNetwork
import time
import json
import logging


logger = logging.getLogger(__name__)


def log(string):
    logger.debug(string)


# A set of exceptions we use to see what goes wrong during asynchronous data transfer waits
class Cancellation(Exception):
    pass


class Failure(Exception):
    pass    


class Timeout(Exception):
    pass
    

class SecondaryServer(QtCore.QObject):

    # Network configuration
    HOST = "lobby.faforever.com"
    TIMEOUT = 5  # seconds

    # Return codes to expect from run()
    RESULT_SUCCESS = 0      # successful
    RESULT_NONE = -1        # operation is still ongoing
    RESULT_FAILURE = 1      # an error occured
    RESULT_CANCEL = 2       # User cancelled
    RESULT_BUSY = 4         # Server is currently busy
    RESULT_PASS = 5         # User refuses to update by canceling
    
    def __init__(self, name, socket, dispatcher, *args, **kwargs):
        """
        Constructor
        """
        QtCore.QObject.__init__(self, *args, **kwargs)
        
        self.name = name
        
        logger = logging.getLogger("faf.secondaryServer.%s" % self.name)
        logger.info("Instantiating secondary server.")
        self.logger = logger
        
        self.socketPort = socket
        self.dispatcher = dispatcher

        self.command = None
        self.message = None
        
        self.blockSize = 0
        self.serverSocket = QtNetwork.QTcpSocket()

        self.serverSocket.error.connect(self.handleServerError)
        self.serverSocket.readyRead.connect(self.readDataFromServer)
        self.serverSocket.connected.connect(self.send_pending)
        self.invisible = False
        self._requests = []
            
    def setInvisible(self):
        self.invisible = True
    
    def send(self, command, *args, **kwargs):
        """ actually do the settings  """
        self._requests += [{'command': command, 'args': args, 'kwargs': kwargs}]
        self.logger.info("Pending requests: {}".format(len(self._requests)))
        if not self.serverSocket.state() == QtNetwork.QAbstractSocket.ConnectedState:
            self.logger.info("Connecting to {}".format(self.name))
            self.serverSocket.connectToHost(self.HOST, self.socketPort)
        else:
            self.send_pending()

    def send_pending(self):
        for req in self._requests:
            self.send_request(req['command'], req['args'], req['kwargs'])
        self._requests = []

    def send_request(self, command, *args, **kwargs):
        self.sendJson(command)

    def sendJson(self, message):
        data = json.dumps(message)
        logger.debug("Outgoing JSON Message: " + data)
        self.writeToServer(data)      

    @QtCore.pyqtSlot()
    def readDataFromServer(self):
        ins = QtCore.QDataStream(self.serverSocket)
        ins.setVersion(QtCore.QDataStream.Qt_4_2)

        while not ins.atEnd():
            if self.blockSize == 0:
                if self.serverSocket.bytesAvailable() < 4:
                    return
                self.blockSize = ins.readUInt32()            
            if self.serverSocket.bytesAvailable() < self.blockSize:
                return
            
            action = ins.readQString()
            self.process(action, ins)
            self.blockSize = 0
            
    def writeToServer(self, action, *args, **kw):               
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
                out.writeQString(str(arg))      

        out.device().seek(0)
        out.writeUInt32(block.size() - 4)

        self.bytesToSend = block.size() - 4        
        self.serverSocket.write(block)

    def process(self, action, stream):
        self.receiveJSON(action, stream)
        
    def receiveJSON(self, data_string, stream):
        """
        A fairly pythonic way to process received strings as JSON messages.
        """
        message = json.loads(data_string)
        logger.debug("answering from server :" + str(message["command"]))
        self.dispatcher.dispatch(message)

    @QtCore.pyqtSlot('QAbstractSocket::SocketError')
    def handleServerError(self, socketError):
        """
        Simple error handler that flags the whole operation as failed, not very graceful but what can you do...
        """
        if socketError == QtNetwork.QAbstractSocket.RemoteHostClosedError:
            log("FA Server down: The server is down for maintenance, please try later.")

        elif socketError == QtNetwork.QAbstractSocket.HostNotFoundError:
            log("Connection to Host lost. Please check the host name and port settings.")
            
        elif socketError == QtNetwork.QAbstractSocket.ConnectionRefusedError:
            log("The connection was refused by the peer.")
        else:
            log("The following error occurred: %s." % self.serverSocket.errorString())    
