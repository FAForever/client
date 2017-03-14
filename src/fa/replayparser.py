

import struct


class ReplayParser:
    def __init__(self, filepath):
        self.file = filepath
    
    def __readline(self, offset, binary):
        line = ''
        while True:
            
            char = struct.unpack("s", binary[offset:offset+1])
    
            offset += 1
            if char[0] == '\r':
                # offset = offset + 2
                break
            elif char[0] == '\x00':
                # offset = offset + 3
                break
            else:
                line = line + char[0]
        return offset, line
        
    def get_version(self):
        f = open(self.file, 'rb')
        binary = f.read()
        offset = 0
        offset, supcom_version = self.__readline(offset, binary)
        f.close()
        if not supcom_version.startswith("Supreme Commander v1"):
            return None
        else:
            return supcom_version.split(".")[-1]
