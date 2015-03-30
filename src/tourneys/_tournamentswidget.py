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
import secondaryServer

from tourneys.tourneyitem import TourneyItem, TourneyItemDelegate


FormClass, BaseClass = util.loadUiType("tournaments/tournaments.ui")


class TournamentsWidget(FormClass, BaseClass):
    ''' list and manage the main tournament lister '''
    
    def __init__(self, client, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)        
        
        self.setupUi(self)

        self.client = client
        self.client.tourneyTab.layout().addWidget(self)
        
        #tournament server
        self.tourneyServer = secondaryServer.SecondaryServer("Tournament", 11001, self)
        self.tourneyServer.setInvisible()

        #Dictionary containing our actual tournaments.
        self.tourneys = {}
  
        self.tourneyList.setItemDelegate(TourneyItemDelegate(self))
        
        self.tourneyList.itemDoubleClicked.connect(self.tourneyDoubleClicked)
        
        self.tourneysTab = {}

        #Special stylesheet       
        self.setStyleSheet(util.readstylesheet("tournaments/formatters/style.css"))

        self.updateTimer = QtCore.QTimer(self)
        self.updateTimer.timeout.connect(self.updateTournaments)
        self.updateTimer.start(600000)
        
    
    def showEvent(self, event):
        self.updateTournaments()
        return BaseClass.showEvent(self, event)

    def updateTournaments(self):
        self.tourneyServer.send(dict(command="get_tournaments"))
        
       
    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def tourneyDoubleClicked(self, item):
        '''
        Slot that attempts to join or leave a tournament.
        ''' 
        if not self.client.login in item.playersname :
            reply = QtGui.QMessageBox.question(self.client, "Register",
                "Do you want to register to this tournament ?",
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:
                self.tourneyServer.send(dict(command="add_participant", uid=item.uid, login=self.client.login))

        else :
            reply = QtGui.QMessageBox.question(self.client, "Register",
                "Do you want to leave this tournament ?",
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:   
                self.tourneyServer.send(dict(command="remove_participant", uid=item.uid, login=self.client.login)) 
    
                
    def handle_tournaments_info(self, message):
        #self.tourneyList.clear()
        tournaments = message["data"]
        for uid in tournaments :
            if not uid in self.tourneys :
                self.tourneys[uid] = TourneyItem(self, uid)
                self.tourneyList.addItem(self.tourneys[uid])
                self.tourneys[uid].update(tournaments[uid], self.client)
            else :
                self.tourneys[uid].update(tournaments[uid], self.client)