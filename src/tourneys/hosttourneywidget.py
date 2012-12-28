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
import util

FormClass, BaseClass = util.loadUiType("tournaments/host.ui")

class HostTourneyWidget(FormClass, BaseClass):
    def __init__(self, parent, item, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)       

        self.setupUi(self)
        self.parent = parent
        
       
        
        self.setStyleSheet(self.parent.client.styleSheet())
        
        self.setWindowTitle ( "Hosting Tournament")
        self.titleEdit.setText ( self.parent.title )
        self.descriptionText.setHtml( self.parent.description )
        self.minRating.setValue ( self.parent.minrating )
        self.maxRating.setValue ( self.parent.maxrating )
        self.minPlayers.setValue ( self.parent.minplayers )
        self.maxPlayers.setValue ( self.parent.maxplayers )
        
        self.dateTimeEdit.setDateTime(QtCore.QDateTime.currentDateTime())       
 
        self.hostButton.released.connect(self.hosting)

    def hosting(self):
        
        self.parent.title = self.titleEdit.text().strip()
        self.parent.description = self.descriptionText.toPlainText ()
        
        self.parent.minrating = self.minRating.value()
        self.parent.maxrating = self.maxRating.value()
        
        self.parent.minplayers = self.minPlayers.value()
        self.parent.maxplayers = self.maxPlayers.value()
        
        self.parent.date = self.dateTimeEdit.dateTime().toUTC().toString("yyyy-MM-dd hh:mm:ss")
        
        self.done(1)
        
