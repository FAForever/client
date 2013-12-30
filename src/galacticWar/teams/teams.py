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

class Teams(object):
    ''' Teams object'''
    def __init__(self, parent):
        self.parent = parent
        self.leader = {}
        self.members = {}
        self.inTeam = False
        
    def setLeader(self, uid, leader):
        self.leader = {}
        self.leader[uid] = leader
    
    def addMember(self, uid, name):
        self.members[uid] = name

    def getLeaderName(self):
        return self.leader.values()[0]
    
    def clearMembers(self):
        self.members = {}
    
    def getMemberNames(self):
        return self.members.values()

    def getMembersUids(self):
        return self.leader.keys() + self.members.keys() 
    
    def getNames(self, players):
        for name in players:
            uid = players[name]
            if uid in self.leader:
                self.leader[uid] = name
            if uid in self.members:
                self.members[uid] = name
                