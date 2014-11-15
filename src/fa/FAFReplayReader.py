
from PyQt4.QtCore import QIODevice, QDataStream, QByteArray
from struct import unpack
import zlib
import json

VERSION = 2

# Reading state
STATE_FAFHEADER = 1
STATE_SCFAHEADER = 2
STATE_SCFADATA = 3

class FAFReplayReader(QIODevice):
    def __init__(self, target_device):
        super(FAFReplayReader, self).__init__()

        super(FAFReplayReader, self).open(QIODevice.ReadOnly)
        self._target_device = target_device

        self._state = STATE_FAFHEADER

        self._fafheader = b''

        self._scfa_header_off = None
        self._scfa_data_off = None
        self._compression = None
        self._reserved = None

        self._pos = 0

        self._zlib_stream = zlib.decompressobj()

    @property
    def header(self):
        assert isinstance(self._fafheader, dict) and 'Header not parsed yet, because stream not read.'
        return self._fafheader

    def _parseFAFHeader(self):
        assert self._fafheader

        ds = QDataStream(QByteArray(self._fafheader))
        ds.setByteOrder(QDataStream.LittleEndian)

        assert ds.readRawData(16) == 'FAF_REPLAY_v%03d\0' % VERSION

        self._scfa_header_off = ds.readUInt32()
        self._scfa_data_off = ds.readUInt32()
        self._compression = ds.readRawData(4)
        self._reserved = ds.readRawData(4)

        self._fafheader = json.loads(ds.readBytes())

    def _readTarget(self, nbytes):
        data = self._target_device.read(nbytes)
        self._pos += len(data)
        return data

    def readData(self, nbytes):
        if self._state == STATE_FAFHEADER:
            required = 36 - len(self._fafheader)
            if required > 0:
                self._fafheader += self._readTarget(required)
                
                if 36 - len(self._fafheader) > 0:
                    return b''
                
            json_len = unpack('<l', self._fafheader[32:36])[0]

            required = json_len + 36 - len(self._fafheader)

            if required > 0:
                self._fafheader += self._readTarget(required)
                
                if json_len + 36 - len(self._fafheader) > 0:
                    return b''

            self._parseFAFHeader()
            self._state = STATE_SCFAHEADER
            return self.read(nbytes)

        elif self._state == STATE_SCFAHEADER:
            data = self._readTarget(min(self._scfa_data_off - self._pos, nbytes))
            if self._pos == self._scfa_data_off:
                self._state = STATE_SCFADATA
            return data
        
        elif self._state == STATE_SCFADATA:
            uncomp = self._zlib_stream.unconsumed_tail
            uncomp += self._readTarget(nbytes - len(uncomp))
            return self._zlib_stream.decompress( uncomp, nbytes)
        
    def close(self):
        self._target_device.close()
        super(FAFReplayReader, self).close()