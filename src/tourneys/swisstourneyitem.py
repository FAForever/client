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
from tourneys.hosttourneywidget import HostTourneyWidget
import client


class SwissTourneyItemDelegate(QtGui.QStyledItemDelegate):
    
    def __init__(self, *args, **kwargs):
        QtGui.QStyledItemDelegate.__init__(self, *args, **kwargs)
        self.height = 125
        
    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
                
        painter.save()
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        if self.height < html.size().height() :
            self.height = html.size().height()
        
       
        option.text = ""  
        option.widget.style().drawControl(QtGui.QStyle.CE_ItemViewItem, option, painter, option.widget)
        
        #Description
        painter.translate(option.rect.left() + 10, option.rect.top()+10)
        clip = QtCore.QRectF(0, 0, option.rect.width() - 10 - 5, option.rect.height())
        html.drawContents(painter, clip)
  
        painter.restore()
        

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        if self.height < html.size().height() :
            self.height = html.size().height()
        return QtCore.QSize(int(html.size().width()+15), int(self.height))  





class SwissTourneyItem(QtGui.QListWidgetItem):
    TEXTWIDTH = 500
    ICONSIZE = 110
    PADDING = 10
    
    WIDTH = ICONSIZE + TEXTWIDTH
    #DATA_PLAYERS = 32
    
    
    FORMATTER_SWISS_OPEN = unicode(util.readfile("tournaments/formatters/swiss_open.qthtml"))

    
    def __init__(self, parent, uid, *args, **kwargs):
        QtGui.QListWidgetItem.__init__(self, *args, **kwargs)

        self.uid = uid
        
        
        
        self.parent = parent
        
        self.type = None    
        self.client = None
        self.title  = None
        self.host   = None
        self.description = None
        self.minplayers = None
        self.maxplayers = None
        self.minrating = None
        self.maxrating = None
        self.date = None
        
        self.state  = None
        
        self.curRound = None

        self.players = []
        self.playersname = []
        
        self.setHidden(True)

    
    def convertTimeToLocal(self, date):
        origdate = QtCore.QDateTime.fromString(date,"yyyy-MM-dd hh:mm:ss")
        origdate.setTimeSpec(QtCore.Qt.UTC)
        
        date = origdate.toLocalTime().toString("dddd dd MMMM")
        year = origdate.toLocalTime().toString("yyyy")
        hour = origdate.toLocalTime().toString("hh:mm")
        return date, year, hour
    
    
    
    def update(self, message, client):
        '''
        Updates this item from the message dictionary supplied
        '''
        self.client  = client
        self.state      = message.get('state', "close")

        if self.state == 'open' or self.state == 'playing' or self.state == 'finished' :
            ''' handling the listing of the tournament '''
            self.title      = message['title']
            self.host       = message['host']
            self.type       = message['type']
        
            self.description= message.get('description', "")
            self.minplayers = message.get('min_players', 2) 
            self.maxplayers = message.get('max_players', 99)
            self.minrating  = message.get('min_rating', 0)
            self.maxrating  = message.get('min_rating', 9999)
            self.curRound  = message.get('current_round', 1)
            self.nbRounds  = message.get('rounds', 1)
            self.players    = message.get('players', [])
            self.date       = message.get('date', QtCore.QDateTime.currentDateTime().toUTC().toString("yyyy-MM-dd hh:mm:ss"))
            
            self.playersname = []
            for player in self.players :
                self.playersname.append(player["name"])
                

            self.description = self.description.replace('\n', '<br>') 
    
            
            playerstring = "<br/>".join(self.playersname)
    
            if self.state == "open" or self.state == "playing" or self.state == "finished":
                date, year, hour = self.convertTimeToLocal(self.date)
                self.setText(self.FORMATTER_SWISS_OPEN.format(date=date, year=year, hour=hour, title=self.title, host=self.host, description=self.description, numreg=str(len(self.playersname)), playerstring=playerstring))
            

            
                
    def pressed(self, item):
        menu = QtGui.QMenu(self.parent)
        
        
        if self.host == self.client.login :

            actionPreview = QtGui.QAction("Preview brackets", menu)
            actionAddPlayer = QtGui.QAction("Add player", menu)
            actionRemovePlayer = QtGui.QAction("Remove player", menu)
            actionEdit = QtGui.QAction("Edit tournament", menu)
            actionStart = QtGui.QAction("Start tournament", menu)
            
            actionDelete = QtGui.QAction("Delete tournament", menu)
            
            actionPreview.triggered.connect(self.preview)
            actionAddPlayer.triggered.connect(self.addPlayer)
            actionRemovePlayer.triggered.connect(self.removePlayer)

            actionEdit.triggered.connect(self.editTourney)
            actionStart.triggered.connect(self.startTourney)
            actionDelete.triggered.connect(self.deleteTourney)
            
            menu.addAction(actionPreview)
            menu.addSeparator()
            menu.addAction(actionAddPlayer)
            menu.addAction(actionRemovePlayer)
            menu.addSeparator()
            menu.addAction(actionEdit)
            menu.addAction(actionStart)
            menu.addSeparator()
            menu.addAction(actionDelete)
                        
            menu.popup(QtGui.QCursor.pos())


    def preview(self):
        self.client.send(dict(command="tournament", action = "preview", uid=self.uid, type = self.type))

    def removePlayer(self):
        item, ok = QtGui.QInputDialog.getItem(self.client, "Removing player", "Player to remove:", self.playersname, 0, False)
        if ok and item:
            self.client.send(dict(command="tournament", action = "remove_player", player=item, uid=self.uid, type = self.type))


    def addPlayer(self):
        player, ok = QtGui.QInputDialog.getText(self.client, "Adding player", "Player name :", QtGui.QLineEdit.Normal, "")
        if ok and player != '':
            self.client.send(dict(command="tournament", action = "add_player", player=player, uid=self.uid, type = self.type))


    def editTourney(self):
        
        hosttourneywidget = HostTourneyWidget(self, self)
        
        
        if hosttourneywidget.exec_() == 1 :
            self.client.send(dict(command="tournament", action = "edit", uid=self.uid, type=self.type, name=self.title, min_players = self.minplayers, max_players = self.maxplayers, min_rating = self.minrating, max_rating = self.maxrating, date = self.date, description = self.description))

    def startTourney(self):
        reply = QtGui.QMessageBox.question(self.client, "Start tournament",
                "Do you want to start to this tournament ? (nobody can register after that)",
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
            self.client.send(dict(command="tournament", action = "start", uid=self.uid, type = self.type))

    def deleteTourney(self):
        reply = QtGui.QMessageBox.question(self.client, "Delete tournament",
            "Do you really want to delete this tournament ?",
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
            self.client.send(dict(command="tournament", action = "delete", uid=self.uid, type = self.type))



    def permutations(self, items):
        """Yields all permutations of the items."""
        if items == []:
            yield []
        else:
            for i in range(len(items)):
                for j in self.permutations(items[:i] + items[i+1:]):
                    yield [items[i]] + j




    def __ge__(self, other):
        ''' Comparison operator used for item list sorting '''        
        return not self.__lt__(other)
    
    
    def __lt__(self, other):
        ''' Comparison operator used for item list sorting '''        
        if not self.client: return True # If not initialized...
        if not other.client: return False;
        
        
        # Default: Alphabetical
        return self.title.lower() < other.title.lower()
    


