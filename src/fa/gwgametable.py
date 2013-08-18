#-------------------------------------------------------------------------------
# Copyright (c) 2013 Gael Honorez.
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

from PyQt4 import QtCore
import util.slpp
import os
import zipfile
import StringIO

def writeTable(upgrades, file):
    ''' write a lua table inside a file '''
    destination = os.path.join(util.APPDATA_DIR, "gamedata", file)
    gwFile = QtCore.QFile(destination)
    gwFile.open(QtCore.QIODevice.WriteOnly)
    lua = util.slpp.SLPP()
    s = StringIO.StringIO()  
    z = zipfile.ZipFile(s, 'w')  
    z.writestr('lua/gwReinforcementList.lua', str(lua.encodeReinforcements(upgrades))) 
    z.close()
    gwFile.write(s.getvalue())
    gwFile.close()
    s.close()