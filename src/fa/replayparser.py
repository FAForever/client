#-------------------------------------------------------------------------------
# Copyright (c) 2012 Gael Honorez.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#-------------------------------------------------------------------------------





import struct

class replayParser:
    def __init__(self, filepath):
        self.file = filepath
    
    def __readLine(self, offset, bin):
        line = ''
        while True :
            
            char = struct.unpack("s", bin[offset:offset+1])
    
            offset = offset + 1
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
