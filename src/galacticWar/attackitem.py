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



from PyQt4 import QtCore, QtGui
import time

class AttackItem(QtGui.QListWidgetItem):
    def __init__(self, uid, *args, **kwargs):
        QtGui.QListWidgetItem.__init__(self, *args, **kwargs)
        
        self.uid            = uid      
        self.timeAttack     = time.time()
        self.itemText        = ""
       
        self.updateTimer    = QtCore.QTimer()
        self.updateTimer.timeout.connect(self.updateText)
        self.updateTimer.start(1000)        

    def update(self, attack, parent):
        '''
        Updates this item from the message dictionary supplied
        '''
        self.parent        = parent
        self.timeAttack    = time.time() + attack["timeAttack"]        

    def updateText(self):
        self.setText("%s [Attack in %i seconds]" % (self.parent.parent.galaxy.get_name(self.uid), (max(0,self.timeAttack - time.time()))))
