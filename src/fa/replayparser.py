
import struct


class replayParser:
    def __init__(self, filepath):
        self.file = filepath

    def __readLine(self, offset, bin_):
        line = b''
        while True:

            char = struct.unpack("s", bin_[offset:offset + 1])

            offset = offset + 1
            if char[0] == b'\r':
                # offset = offset + 2
                break
            elif char[0] == b'\x00':
                # offset = offset + 3
                break
            else:
                line = line + char[0]
        try:
            line = line.decode('utf-8')
        except UnicodeDecodeError:
            line = ''
        return offset, line

    def getVersion(self):
        with open(self.file, 'rb') as f:
            bin_ = f.read()
            offset = 0
            offset, supcomVersion = self.__readLine(offset, bin_)
        if not supcomVersion.startswith("Supreme Commander v1"):
            return None
        else:
            return supcomVersion.split(".")[-1]

    def getMapName(self):
        with open(self.file, 'rb') as f:
            bin_ = f.read()
            offset = 45
            offset, mapname = self.__readLine(offset, bin_)
        if not mapname.strip().startswith("/maps/"):
            return 'None'
        else:
            return mapname.split('/')[2]
