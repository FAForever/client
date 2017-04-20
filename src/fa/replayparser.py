



import struct

class replayParser:
    def __init__(self, filepath):
        self.file = filepath
    
    def __readLine(self, offset, bin):
        line = b''
        while True :
            
            char = struct.unpack("s", bin[offset:offset+1])
    
            offset = offset + 1
            if char[0] == b'\r':
                #offset = offset + 2
                break
            elif char[0] == b'\x00':
                #offset = offset + 3
                break
            else:
                line = line + char[0]
        try:
            line = line.decode('utf-8')
        except UnicodeDecodeError:
            line = ''
        return offset, line
        
    def getVersion(self):
        f = open(self.file, 'rb')
        bin = f.read() 
        offset= 0
        offset, supcomVersion = self.__readLine(offset, bin)  
        f.close()
        if (supcomVersion.startswith("Supreme Commander v1") == False) :     
            return None
        else :
            return supcomVersion.split(".")[-1]
