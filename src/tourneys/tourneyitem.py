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

import math

from fa import maps
import util
from tourneys.tourneytypeitem import tourneyType

from trueSkill.Team import *
from trueSkill.Teams import *
from trueSkill.TrueSkill.FactorGraphTrueSkillCalculator import * 
from trueSkill.Rating import *

import client


class TourneyItemDelegate(QtGui.QStyledItemDelegate):
    
    def __init__(self, *args, **kwargs):
        QtGui.QStyledItemDelegate.__init__(self, *args, **kwargs)
        
    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
                
        painter.save()
        painter.setRenderHint(8, True)
        
        
        rounds = option.widget.item(index.row()).rounds

    
        players = option.widget.item(index.row()).maxPlayers
        numGames = option.widget.item(index.row()).numGames
        
        firstRoundByes = math.pow(2,rounds) - players
        
        firstRoundGames = int(option.widget.item(index.row()).firstRoundGames)
        
        junctionsFrom = {}
        junctionsTo = {}
        junctionsGotBye = {}
        
        numMatches = 0
        
        leftMarging = 5
        
        playerNum = players
        
        for i in xrange(rounds) :

            offset = 1
            
            if i == 0 :
                offset = 1.1
                numMatches = firstRoundGames
            elif i == 1 :
                numMatches = (float(firstRoundGames) / 2) + (firstRoundByes / 2)

            else :
                numMatches = numMatches / 2

            
            topMarging =  ((TourneyItem.HEIGHT * offset) - (numMatches * (TourneyItem.HEIGHTMATCH + TourneyItem.SPACING))) / 2
            
            junctionsGotBye[i] = []
            
            if i != 0 :
                junctionsFrom[i] = []
            if numMatches > 1 :
                junctionsTo[i] = []
                
            for j in xrange(int(numMatches)) :

                painter.fillRect(leftMarging, topMarging, TourneyItem.WIDTHMATCH, TourneyItem.HEIGHTMATCH, QtGui.QColor("#202020"))
                
                painter.drawRoundedRect(leftMarging+1, topMarging+1, TourneyItem.WIDTHMATCH-1, (TourneyItem.HEIGHTMATCH/2)-1, 5, 5)
                painter.drawRoundedRect(leftMarging+1, topMarging+TourneyItem.HEIGHTMATCH/2, TourneyItem.WIDTHMATCH-1, (TourneyItem.HEIGHTMATCH/2)-1, 5, 5)
                
                painter.drawLine(leftMarging+1+(TourneyItem.WIDTHMATCH * .1), topMarging+1, leftMarging+1+(TourneyItem.WIDTHMATCH * .1), TourneyItem.HEIGHTMATCH+topMarging-1)
                
                if i == 0 :
                    painter.drawText(leftMarging+1, topMarging+1, (TourneyItem.WIDTHMATCH-1) *.1, (TourneyItem.HEIGHTMATCH/2)-1, QtCore.Qt.AlignCenter, str(playerNum))
                    playerNum -= 1
                    painter.drawText(leftMarging+1, topMarging+TourneyItem.HEIGHTMATCH/2, (TourneyItem.WIDTHMATCH-1) *.1, (TourneyItem.HEIGHTMATCH/2)-1, QtCore.Qt.AlignCenter, str(playerNum))
                    playerNum -= 1
                elif i == 1 :
                    if firstRoundByes != 0 and playerNum > 0 :
                        painter.drawText(leftMarging+1, topMarging+1, (TourneyItem.WIDTHMATCH-1) *.1, (TourneyItem.HEIGHTMATCH/2)-1, QtCore.Qt.AlignCenter, str(playerNum))
                        playerNum -= 1
                        junctionsGotBye[i].append(j)
                        
                        
                if i != 0 :
                    junctionsFrom[i].append( QtCore.QPointF(leftMarging, topMarging+TourneyItem.HEIGHTMATCH/2) )
                
                if numMatches > 1 :
                    junctionsTo[i].append(QtCore.QPointF(leftMarging+TourneyItem.WIDTHMATCH, topMarging+TourneyItem.HEIGHTMATCH/2))
            
                            
                topMarging = topMarging + TourneyItem.SPACING + TourneyItem.HEIGHTMATCH
                

            

            
            leftMarging = leftMarging + TourneyItem.WIDTHMATCH + TourneyItem.HSPACING
        #round 1
        
        pen = QtGui.QPen(painter.pen())
        pen.setWidthF(2)
        painter.setPen(pen)
                
        for key in junctionsTo :
            fromLength = len(junctionsFrom[key+1])
            toLength = len(junctionsTo[key])
            print fromLength
            print toLength
            if fromLength == toLength : 
                for i in range(toLength) :         
                    
                    start = junctionsTo[key][i]
                    end = junctionsFrom[key+1][i]
                    self.drawLiasion(painter, start, end)

                    
            elif (toLength / 2) == fromLength :
                idx = 0
                for i in range(fromLength) :
                    end = junctionsFrom[key+1][i]
                    start = junctionsTo[key][idx]
                    idx += 1
                    start2 = junctionsTo[key][idx]
                    idx += 1
                    self.drawLiasion(painter, start, end)                       
                    self.drawLiasion(painter, start2, end)
                  
            else :
                idx = 0
                for i in range(toLength) :

                    start = junctionsTo[key][i]
                    end = junctionsFrom[key+1][idx]
                    
                    if i in junctionsGotBye[key+1] :
                        idx += 1


                    self.drawLiasion(painter, start, end)

                  
  
        painter.restore()
   
    def drawLiasion(self, painter, start, end):
        painter.drawLine(start.x(), start.y(), start.x() + TourneyItem.HSPACING / 2, start.y())
        painter.drawLine(start.x() + TourneyItem.HSPACING / 2, start.y(), end.x()- TourneyItem.HSPACING / 2, end.y())                    
        painter.drawLine(end.x()- TourneyItem.HSPACING / 2, end.y(), end.x(), end.y())


    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
        
#        html = QtGui.QTextDocument()
#        html.setHtml(option.text)
#        html.setTextWidth(TourneyItem.TEXTWIDTH)
        return QtCore.QSize(option.widget.width(), TourneyItem.HEIGHT)  





class TourneyItem(QtGui.QListWidgetItem):
    HEIGHT = 500
    HEIGHTMATCH = 62
    WIDTHMATCH = 200
    SPACING = 10
    HSPACING = 50
    

    #DATA_PLAYERS = 32
    
    
#    FORMATTER_FAF = unicode(util.readfile("games/formatters/faf.qthtml"))
#    FORMATTER_MOD = unicode(util.readfile("games/formatters/mod.qthtml"))
    
    def __init__(self, uid, *args, **kwargs):
        QtGui.QListWidgetItem.__init__(self, *args, **kwargs)

        self.uid = uid
        self.client = None
        self.title  = None
        self.host   = None
        self.mod    = None
        self.moddisplayname  = None
        self.state  = None
        self.options = []
        self.players = []
        self.minPlayers = 2
        self.maxPlayers = 2
        
        self.numGames = self.maxPlayers - 1
        
        self.rounds = int(math.ceil(math.log(self.maxPlayers, 2)))
        self.firstRoundGames = self.maxPlayers - self.next_power_of_2(self.maxPlayers)
        
        self.setHidden(True)
        

             
    def update(self, message, client):
        '''
        Updates this item from the message dictionary supplied
        '''

        self.client  = client
        self.title      = message['title']
        self.minPlayers = message['min_players']
        self.maxPlayers = message['max_players']
        self.host       = message['host']
        
        
        oldstate = self.state
        self.state  = message['state']
   
        self.setHidden((self.state != 'open'))       

        self.rounds = int(math.ceil(math.log(self.maxPlayers, 2)))
        self.numGames = self.maxPlayers - 1

        self.firstRoundGames = self.maxPlayers - self.next_power_of_2(self.maxPlayers)
        
    def next_power_of_2(self, v):
        if math.log(v, 2) % 1.0 == 0.0 :
            v -= 1
        return pow(2,math.floor(math.log(v) / math.log(2))) 
