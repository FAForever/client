
from PyQt4.QtCore import QIODevice, QDataStream, QByteArray
import zlib
import json

VERSION = 2

class NoSCFAHeader(Exception):
    pass

def TryGetSCFAReplayHeader(byteArray):
    stream = QDataStream(byteArray)
    stream.setByteOrder(QDataStream.LittleEndian)

    def readUI8():
        r = ord(stream.readUInt8())
        if stream.atEnd():
            raise NoSCFAHeader()
        return r

    def readUI32():
        r = stream.readUInt32()
        if stream.atEnd():
            raise NoSCFAHeader()
        return r

    def readNulStr():
        byte = readUI8()
        buf = bytearray()
        while byte != 0:
            buf += bytearray([byte])
            byte = readUI8()
        return buf.decode()

    def skip(nbytes):
        stream.skipRawData(nbytes)

    readNulStr() # engine version
    readNulStr() #
    readNulStr() # Replay v1.9\r\n/maps/Map/File.scmap
    readNulStr() # foek knoes

    mods_size = readUI32()
    skip(mods_size)

    scenario_size = readUI32()
    skip(scenario_size)

    n_sources = readUI8()
    for i in range(n_sources):
        readNulStr() # name
        readUI32() # timeouts rem

    readUI8() # cheats

    n_armies = readUI8()
    for i in range(n_armies):
        data_size = readUI32()
        skip(data_size)
        readUI8() # source_id
        readUI8() # unknown

    readUI32() # random_seed

    size = stream.device().pos()
    return byteArray[:size], byteArray[size:]

class FAFReplayWriter(QIODevice):
    def __init__(self, target_device):
        super(FAFReplayWriter, self).__init__()

        assert isinstance(target_device, QIODevice)

        super(FAFReplayWriter, self).open(QIODevice.WriteOnly)
        self._target_device = target_device

        self._header_given = False

        self._scfa_header_off = 0
        self._scfa_tick_off = 0
        self._scfa_tick_compress = 'ZLIB'
        self._header_reserved = 0

        self._faf_header = None

        self._header_written = False

        self._scfa_lazybuf = QByteArray()
        self._scfa_header = None

        self._zlib_stream = zlib.compressobj()

    def writeHeader(self, header):
        assert not self._header_given
        assert isinstance(header, dict)
        self._header_given = True

        self._target_device.write(b'FAF_REPLAY_v%03d\0' % VERSION)

        self._faf_header = json.dumps(header).encode()

    def _finalizeHeader(self):
        assert self._header_given
        assert self._scfa_header
        assert self._faf_header

        ds = QDataStream(self._target_device)
        ds.setByteOrder(QDataStream.LittleEndian)

        ds.writeUInt32( 32 + 4 + len(self._faf_header) )
        ds.writeUInt32( 32 + 4 + len(self._faf_header) + len(self._scfa_header))
        ds.device().write(self._scfa_tick_compress)
        ds.writeUInt32(0) # reserved

        # Write faf json header
        ds.writeBytes(self._faf_header)
        self._faf_header = None

        # Write scfa header
        self._target_device.write(self._scfa_header)
        self._scfa_header = None

        self._header_written = True

    def readData(self, p_int):
        return 0

    def writeData(self, p_str):
        if self._scfa_lazybuf is not None:
            self._scfa_lazybuf += p_str
            try:
                head, ticks = TryGetSCFAReplayHeader(self._scfa_lazybuf)
                self._scfa_header = head
                self._finalizeHeader()
                self._target_device.write(self._zlib_stream.compress(ticks))
                self._scfa_lazybuf = None
            except NoSCFAHeader:
                pass
        else:
            self._target_device.write(self._zlib_stream.compress(p_str))
        return len(p_str)

    def close(self):
        self._target_device.write(self._zlib_stream.flush())
