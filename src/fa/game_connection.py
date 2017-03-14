from PyQt4.QtCore import QObject, pyqtSignal, QDataStream
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
        self._socket.readyRead.connect(self._on_ready_read)
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
            ds.writeRawData(self._pack_lua_val(chunk))

    def _pack_lua_val(self, val):
        if isinstance(val, int):
            return pack("=bi", 0, val)
        elif isinstance(val, unicode) or isinstance(val, str):
            return pack("=bi%ds" % len(val), 1, len(val), val.encode())
        else:
            raise Exception("Unknown GameConnection Field Type: %s" % type(val))

    def _read_lua_val(self, ds):
        if self._socket.bytesAvailable() < 5:
            return None

        field_type, field_size = unpack('=bl', self._socket.peek(5))

        if field_type == 0:
            ds.readRawData(5)
            return field_size
        elif field_type == 1:
            if self._socket.bytesAvailable() < field_size + 5:
                return None

            ds.readRawData(5)

            data_str = ds.readRawData(field_size).decode('utf-8')
            fixed_str = data_str.replace("/t", "\t").replace("/n", "\n")

            return unicode(fixed_str)
        else:
            raise Exception("Unknown GameConnection Field Type: %d" % field_type)

    # Non-reentrant
    def _on_ready_read(self):
        while self._socket.bytesAvailable() >= 4:
            ds = QDataStream(self._socket)
            ds.setByteOrder(QDataStream.LittleEndian)

            # Header packet
            if self.header is None:
                size, = unpack('=l', self._socket.peek(4))

                if self._socket.bytesAvailable() < size + 4:
                    return

                # Omit size
                ds.readUInt32()

                self.header = ds.readRawData(size).decode()

            # Chunks packet
            else:
                if self.nchunks == -1:
                    self.nchunks = ds.readUInt32()
                    self.chunks = []

                while len(self.chunks) < self.nchunks:
                    chunk = self._read_lua_val(ds)

                    if chunk is None:
                        return

                    self.chunks.append(chunk)

                # Packet pair reading done.
                self._logger.info("GC >> : %s : %s", self.header, self.chunks)
                self.messageReceived.emit(self.header, self.chunks)
                self.header = None
                self.nchunks = -1
                self.chunks = None
