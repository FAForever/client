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

tourneyType = {}


class TourneyTypeItem(QtGui.QListWidgetItem):
    def __init__(self, message, *args, **kwargs):
        QtGui.QListWidgetItem.__init__(self, *args, **kwargs)

        self.tourney = message["name"]
        self.name = message["fullname"]
        #self.mod = message["mod"]

        #Load Icon and Tooltip

        tip = message["desc"]      
        self.setToolTip(tip)
        
        if message["icon"] == None :
            icon = util.icon("games/mods/faf.png")        
            self.setIcon(icon)
        else :
            # TODO : download the icon from the remote path.
            pass

        color = client.instance.getColor("player")
        self.setTextColor(QtGui.QColor(color))
        self.setText(self.name)


    def __ge__(self, other):
        ''' Comparison operator used for item list sorting '''        
        return not self.__lt__(other)
    
    
    def __lt__(self, other):
        ''' Comparison operator used for item list sorting '''        

        # Default: Alphabetical
        return self.name.lower() < other.tourney.lower()
    



