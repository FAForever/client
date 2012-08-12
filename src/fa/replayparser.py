import struct

class replayParser:
    def __init__(self, filepath):
        self.file = filepath
    
    def __readLine(self, offset, bin):
        line = ''
        while True :
            
            char = struct.unpack("s", bin[offset:offset+1])
    
            offset = offset + 1
            #print char
            if char[0] == '\r' :
                #offset = offset + 2
                break
            elif char[0] == '\x00' :
                #offset = offset + 3
                break
            else :
                line = line + char[0]
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
