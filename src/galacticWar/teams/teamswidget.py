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

from PyQt4 import QtCore, QtGui

import util
import copy
import logging

logger = logging.getLogger("gw.teamwidget")
logger.setLevel(logging.DEBUG)

FormClass, BaseClass = util.loadUiType("galacticwar/teams.ui")

class TeamWidget(FormClass, BaseClass):
    def __init__(self, client, players, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)
        
        self.setupUi(self)
        self.client = client
        self.players = players
        
        self.playerList.clear()
        self.playerList.itemDoubleClicked.connect(self.proposeTeam)
        self.client.teamUpdated.connect(self.updateStatus)
        
    def update(self, players):
        ''' update the player list '''
        self.players = copy.deepcopy(players)
        if self.client.client.login in self.players:
            del self.players[self.client.client.login]  
        self.playerList.clear()
        self.playerList.addItems(self.players.keys())       

        for name in self.client.teams.getMemberNames():
            item = self.playerList.findItems(name, QtCore.Qt.MatchExactly)
            if len(item)==1:
                item[0].setForeground(QtCore.Qt.green)
            continue         
    
    def updateStatus(self, message):
        members = message["members"]
        for uid in members:
            if uid in self.players.values():
                name = self.players.keys()[self.players.values().index(uid)]
                item = self.playerList.findItems(name, QtCore.Qt.MatchExactly)
                if len(item)==1:
                    item[0].setForeground(QtCore.Qt.green)
                continue
            
    def proposeTeam(self, item):
        ''' Propose a team with a player '''
        if item.text() in self.players:
            #self.client.send(dict(command="request_team", uid=5))
            self.client.send(dict(command="request_team", uid=self.players[item.text()]))
            
        
                