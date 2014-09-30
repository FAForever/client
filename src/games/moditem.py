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





from PyQt4 import QtGui
import util
import client
import os

# These mods are always on top

mods = {}

mod_crucial = ["faf"]

# These mods are not shown in the game list
mod_invisible = []

mod_favourites = []  # LATER: Make these saveable and load them from settings

class ModItem(QtGui.QListWidgetItem):
    def __init__(self, message, *args, **kwargs):
        QtGui.QListWidgetItem.__init__(self, *args, **kwargs)

        self.mod  = message["name"]
        self.name = message["fullname"]
        self.options = message["options"]
        #Load Icon and Tooltip

        tip = message["desc"]      
        self.setToolTip(tip)
        
        if message["icon"] is None:
            icon = util.icon(os.path.join("games/mods/", self.mod + ".png"))
            if icon.isNull():
                icon = util.icon("games/mods/default.png")
            self.setIcon(icon)
        else :
            # TODO : download the icon from the remote path.
            pass
        
        
        if  self.mod in mod_crucial:
            color = client.instance.getColor("self")
        else:
            color = client.instance.getColor("player")
            
        self.setTextColor(QtGui.QColor(color))
        self.setText(self.name)


    def __ge__(self, other):
        ''' Comparison operator used for item list sorting '''        
        return not self.__lt__(other)
    
    
    def __lt__(self, other):
        ''' Comparison operator used for item list sorting '''        
        
        # Crucial Mods are on top
        if (self.mod in mod_crucial) and not (other.mod in mod_crucial): return True
        if not (self.mod in mod_crucial) and (other.mod in mod_crucial): return False
        
        # Favourites are also ranked up top
        if (self.mod in mod_favourites) and not (other.mod in mod_favourites): return True
        if not(self.mod in mod_favourites) and (other.mod in mod_favourites): return False
        
        # Default: Alphabetical
        return self.name.lower() < other.mod.lower()
    



