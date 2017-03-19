from PyQt5.QtCore import QObject, pyqtSignal, QDataStream
from struct import pack, unpack

from decorators import with_logger


@with_logger
class GPGNetConnection(QObject):
    """
    Represents a local 'GPGNet' connection from the game
    """

    messageReceived = pyqtSignal(str, list)
    closed = pyqtSignal()

    def __init__(self, tcp_connection):
        super(GPGNetConnection, self).__init__()
        self._socket = tcp_connection
        self._socket.readyRead.connect(self._onReadyRead)
        self._socket.disconnected.connect(lambda: self.closed.emit())
        self.header = None
        self.nchunks = -1
        self.chunks = None

    def send(self, command, *args):
        self._logger.info("GC<<: {}:{}".format(command, args))
        ds = QDataStream(self._socket)
        ds.setByteOrder(QDataStream.LittleEndian)

        # Header
        ds.writeUInt32(len(command))
        ds.writeRawData(command.encode())

        # Chunks
        ds.writeUInt32(len(args))

        for chunk in args:
            ds.writeRawData(self._packLuaVal(chunk))

    def _packLuaVal(self, val):
        if isinstance(val, int):
            return pack("=bi", 0, val)
        elif isinstance(val, str) or isinstance(val, str):
            return pack("=bi%ds" % len(val), 1, len(val), val.encode())
        else:
            raise Exception("Unknown GameConnection Field Type: %s" % type(val))

    def _readLuaVal(self, ds):
        if self._socket.bytesAvailable() < 5:
            return None

        fieldType, fieldSize = unpack('=bl', self._socket.peek(5))

        if fieldType == 0:
            ds.readRawData(5)
            return fieldSize
        elif fieldType == 1:
            if self._socket.bytesAvailable() < fieldSize + 5:
                return None

            ds.readRawData(5)

            datastring = ds.readRawData(fieldSize).decode('utf-8')
            fixedStr = datastring.replace("/t","\t").replace("/n","\n")

            return str(fixedStr)
        else:
            raise Exception("Unknown GameConnection Field Type: %d" % fieldType)

    # Non-reentrant
    def _onReadyRead(self):
        while self._socket.bytesAvailable() >= 4:
            ds = QDataStream(self._socket)
            ds.setByteOrder(QDataStream.LittleEndian)

            # Header packet
            if self.header is None:
                size, = unpack('=l', self._socket.peek(4))

                if self._socket.bytesAvailable() < size + 4:
                    return

                #Omit size
                ds.readUInt32()

                self.header = ds.readRawData(size).decode()

            # Chunks packet
            else:
                if self.nchunks == -1:
                    self.nchunks = ds.readUInt32()
                    self.chunks = []

                while len(self.chunks) < self.nchunks:
                    chunk = self._readLuaVal(ds)

                    if chunk is None:
                        return

                    self.chunks.append(chunk)

                # Packet pair reading done.
                self._logger.info("GC >> : %s : %s", self.header, self.chunks)
                self.messageReceived.emit(self.header, self.chunks)
                self.header = None
                self.nchunks = -1
                self.chunks = None
