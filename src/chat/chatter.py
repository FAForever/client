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





from PyQt4 import QtGui, QtCore

from chat._avatarWidget import avatarWidget

from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkRequest
from chat import user2name
import util

import fa
import client


class Chatter(QtGui.QTableWidgetItem):
    SORT_COLUMN = 2
    AVATAR_COLUMN = 1
    RANK_COLUMN = 0
    STATUS_COLUMN = 3    
            
    '''
    A chatter is the representation of a person on IRC, in a channel's nick list. There are multiple chatters per channel.
    There can be multiple chatters for every Player in the Client.
    '''
    def __init__(self, parent, user, lobby, *args, **kwargs):
        QtGui.QTableWidgetItem.__init__(self, *args, **kwargs)
                
        #TODO: for now, userflags and ranks aren't properly interpreted :-/ This is impractical if an operator reconnects too late.
        self.parent = parent
        self.lobby = lobby

        if user[0] in self.lobby.OPERATOR_COLORS:
            self.elevation = user[0]
        else:
            self.elevation = None

        self.name = user2name(user)
        
        self.avatar = None
        self.status = None
        self.rating = None
        self.country = None
        self.league = None
        
        self.setText(self.name)
        self.setFlags(QtCore.Qt.ItemIsEnabled)        
        self.setTextAlignment(QtCore.Qt.AlignLeft)

        row = self.parent.rowCount()
        self.parent.insertRow(row)
        
        self.parent.setItem(row, Chatter.SORT_COLUMN, self)
        
        self.avatarItem = QtGui.QTableWidgetItem()
        self.avatarItem.setFlags(QtCore.Qt.ItemIsEnabled)
        self.avatarItem.setTextAlignment(QtCore.Qt.AlignHCenter)
        
        self.rankItem = QtGui.QTableWidgetItem()
        self.rankItem.setFlags(QtCore.Qt.ItemIsEnabled)
        self.rankItem.setTextAlignment(QtCore.Qt.AlignHCenter)

        self.statusItem = QtGui.QTableWidgetItem()
        self.statusItem.setFlags(QtCore.Qt.ItemIsEnabled)
        self.statusItem.setTextAlignment(QtCore.Qt.AlignHCenter)


        self.parent.setItem(self.row(), Chatter.RANK_COLUMN, self.rankItem)
        self.parent.setItem(self.row(), Chatter.AVATAR_COLUMN, self.avatarItem)
        self.parent.setItem(self.row(), Chatter.STATUS_COLUMN, self.statusItem)

        self.update()        


    def setVisible(self, visible):        
        if visible:
            self.tableWidget().showRow(self.row())
        else:
            self.tableWidget().hideRow(self.row())
              
    def __ge__(self, other):
        ''' Comparison operator used for item list sorting '''        
        return not self.__lt__(other)
    
    
    def __lt__(self, other):
        ''' Comparison operator used for item list sorting '''        
        
        # Everyone is compared by operator status, operators are > everyone, just like in real life
        # CAVEAT: This is actually arbitrary because the dict isn't guaranteed to be the 'correct' order
        if self.elevation and other.elevation: return self.lobby.OPERATOR_COLORS.keys().index(self.elevation) < self.lobby.OPERATOR_COLORS.keys().index(other.elevation)
        if self.elevation and not other.elevation: return True
        if not self.elevation and other.elevation: return False
        
        # Non-Operators will be compared for friendship and actual player (not civilian) status
        if self.lobby.client.isFriend(self.name) and not self.lobby.client.isFriend(other.name): return True
        if not self.lobby.client.isFriend(self.name) and self.lobby.client.isFriend(other.name): return False
        if self.lobby.client.isPlayer(self.name) and not self.lobby.client.isPlayer(other.name): return True 
        if not self.lobby.client.isPlayer(self.name) and self.lobby.client.isPlayer(other.name): return False
        
        # List self below all friends and above every other player 
        if self.name == self.lobby.client.login: return True
        if other.name == self.lobby.client.login: return False
        
        # Default: Alphabetical
        return self.name.lower() < other.name.lower()
 
    
    def updateAvatar(self):
        #TODO: This has a few rough edges and needs to work with a global QNetworkAccessManager. 
        if self.avatar:        
            
            self.avatarTip = self.avatar["tooltip"]
            
            #if self.name == "thygrrr":
            #    self.avatar["url"] = "http://thygrrr.de/faf/thygrrr.png"

            url = self.avatar["url"]
            
            
            avatarPix = util.respix(url) 
                    
            if avatarPix :
                self.avatarItem.setIcon(QtGui.QIcon(avatarPix))            
                self.avatarItem.setToolTip(self.avatarTip)
            else:                           
                if util.addcurDownloadAvatar(url, self.name) :                
                    self.nam = QNetworkAccessManager()
                    self.nam.finished.connect(self.lobby.finishDownloadAvatar)
                    self.nam.get(QNetworkRequest(QtCore.QUrl(url)))            
        else:
            # No avatar set.
            self.avatarItem.setIcon(None)            
            self.avatarItem.setToolTip(None)
            
                        
                            
    def update(self):
        '''
        updates the appearance of this chatter in the nicklist according to its lobby and irc states 
        '''        

        country = self.lobby.client.getUserCountry(self.name)

        if  country != None :
            self.setIcon(util.icon("chat/countries/%s.png" % country))
            self.setToolTip(country)
            
        
        if self.lobby.client.getUserAvatar(self.name) != self.avatar:            
            self.avatar = self.lobby.client.getUserAvatar(self.name)
            self.updateAvatar()

        self.rating = self.lobby.client.getUserRanking(self.name)

        # Color handling
        if self.elevation in self.lobby.OPERATOR_COLORS:            
            self.setTextColor(QtGui.QColor(self.lobby.OPERATOR_COLORS[self.elevation]))
        else:
            self.setTextColor(QtGui.QColor(self.lobby.client.getUserColor(self.name)))

        rating = self.rating

        # Status icon handling
        if self.name in client.instance.urls:
            url = client.instance.urls[self.name]
            if url.scheme() == "fafgame":
                self.statusItem.setIcon(util.icon("chat/status/lobby.png"))
                self.statusItem.setToolTip("In Game Lobby<br/>"+url.toString())
            elif url.scheme() == "faflive":
                self.statusItem.setIcon(util.icon("chat/status/playing.png"))
                self.statusItem.setToolTip("Playing Game<br/>"+url.toString())
        else:
                self.statusItem.setIcon(QtGui.QIcon())
                self.statusItem.setToolTip("Idle")
            

        #Rating icon choice
        #TODO: These are very basic and primitive
        if rating != None:            
                league = self.lobby.client.getUserLeague(self.name)
                
                self.rankItem.setToolTip("Global Rating: " + str(int(rating)))  
                
                if league != None :        
                    self.rankItem.setToolTip("Division : " + league["division"]+ "\nGlobal Rating: " + str(int(rating)))
                    if league["league"] == 1 :
                        self.league = "chat/rank/Aeon_Scout.png"
                        self.rankItem.setIcon(util.icon("chat/rank/Aeon_Scout.png"))
                    elif league["league"] == 2 :
                        self.league = "chat/rank/Aeon_T1.png"
                        self.rankItem.setIcon(util.icon("chat/rank/Aeon_T1.png"))
                    elif league["league"] == 3 :
                        self.league = "chat/rank/Aeon_T2.png"
                        self.rankItem.setIcon(util.icon("chat/rank/Aeon_T2.png"))
                    elif league["league"] == 4 :
                        self.league = "chat/rank/Aeon_T3.png"
                        self.rankItem.setIcon(util.icon("chat/rank/Aeon_T3.png"))
                    elif league["league"] == 5 :                
                        self.league = "chat/rank/Aeon_XP.png"        
                        self.rankItem.setIcon(util.icon("chat/rank/Aeon_XP.png"))
                else :
                    self.league = "chat/rank/newplayer.png"
                    self.rankItem.setIcon(util.icon("chat/rank/newplayer.png"))
                    
        else:
                self.rankItem.setIcon(util.icon("chat/rank/civilian.png"))
                self.rankItem.setToolTip("IRC User")
            
    def joinChannel(self):
        channel, ok = QtGui.QInputDialog.getText(self.lobby.client, "QInputDialog.getText()", "Channel :", QtGui.QLineEdit.Normal, "#tournament")
        if ok and channel != '':
            self.lobby.client.joinChannel(self.name, channel)
            

    def addAvatar(self):
        avatarSelection = avatarWidget(self.lobby.client, self.name)
        avatarSelection.exec_()
        
    def addFriend(self):
        self.lobby.client.addFriend(self.name)
        
        
    def remFriend(self):
        self.lobby.client.remFriend(self.name)
   
    def kick(self):
        pass
    
    def closeFA(self):
        self.lobby.client.closeFA(self.name)

    def closeLobby(self):
        self.lobby.client.closeLobby(self.name)
    
    def doubleClicked(self, item):
        # Chatter name clicked
        if item == self:      
            self.lobby.openQuery(self.name, True) #open and activate query window        
        elif item == self.statusItem:                                          
            if self.lobby.client.login != self.name:
                if self.name in client.instance.urls:
                    url = client.instance.urls[self.name]
                    if url.scheme() == "fafgame":
                        self.joinInGame()
                    elif url.scheme() == "faflive":
                        self.viewReplay()


        
    def pressed(self, item):        
        menu = QtGui.QMenu(self.parent)

        # Actions for stats
        
        actionStats = QtGui.QAction("View Player statistics", menu)
        
        # Actions for Games and Replays
        actionReplay = QtGui.QAction("View Live Replay", menu)
        
        actionJoin = QtGui.QAction("Join in Game", menu)
        actionInvite = QtGui.QAction("Invite to Game", menu)

        
        # Default is all disabled, we figure out what we can do after this
        actionReplay.setDisabled(True)
        actionJoin.setDisabled(True)
        actionInvite.setDisabled(True)

                
        # Don't allow self to be invited to a game, or join one
        if self.lobby.client.login != self.name:
            if self.name in client.instance.urls:
                url = client.instance.urls[self.name]
                if url.scheme() == "fafgame":
                    actionJoin.setEnabled(True)
                elif url.scheme() == "faflive":
                    actionReplay.setEnabled(True)
                

        # Triggers
        actionStats.triggered.connect(self.viewStats)
        actionReplay.triggered.connect(self.viewReplay)
        actionJoin.triggered.connect(self.joinInGame)
        actionInvite.triggered.connect(self.invite)
      
        # power menu
        if self.lobby.client.power > 1 :
            # admin and mod menus
            actionAddAvatar = QtGui.QAction("Assign avatar", menu)
            menu.addAction(actionAddAvatar)
            actionAddAvatar.triggered.connect(self.addAvatar)
            
            actionJoinChannel = QtGui.QAction("Join Channel", menu)
            menu.addAction(actionJoinChannel)
            actionJoinChannel.triggered.connect(self.joinChannel)

            actionKick = QtGui.QAction("Kick", menu)
            menu.addAction(actionKick)
            actionKick.triggered.connect(self.kick)
            actionKick.setDisabled(1)

            if self.lobby.client.power == 2 :
                actionCloseFA = QtGui.QAction("Close FA", menu)
                menu.addAction(actionCloseFA)
                actionCloseFA.triggered.connect(self.closeFA)

                actionCloseLobby = QtGui.QAction("Kick from Lobby", menu)
                menu.addAction(actionCloseLobby)
                actionCloseLobby.triggered.connect(self.closeLobby)                
      
            menu.addSeparator()
            
            
        
        # Adding to menu
        menu.addAction(actionStats)
        menu.addSeparator()
        menu.addAction(actionReplay)
        menu.addAction(actionJoin)
        menu.addAction(actionInvite)
        menu.addSeparator()
            

        
        # Actions for the Friend List
        actionAddFriend = QtGui.QAction("Add friend", menu)
        actionRemFriend = QtGui.QAction("Remove friend", menu)
        
        # Don't allow self to be added or removed from friends
        if self.lobby.client.login == self.name:
            actionAddFriend.setDisabled(1)
            actionRemFriend.setDisabled(1)
              
        # Enable / Disable actions according to friend status  
        if self.lobby.client.isFriend(self.name):
            actionAddFriend.setDisabled(1)
        else :
            actionRemFriend.setDisabled(1)
                                      
        # Triggers
        actionAddFriend.triggered.connect(self.addFriend)
        actionRemFriend.triggered.connect(self.remFriend)
      
        # Adding to menu
        menu.addAction(actionAddFriend)
        menu.addAction(actionRemFriend)


        #Finally: Show the popup
        menu.popup(QtGui.QCursor.pos())
            
    @QtCore.pyqtSlot()
    def viewStats(self):
        if self.name in self.lobby.client.players :
            self.lobby.client.profile.setplayer(self.name)
            self.lobby.client.profile.show() 
        

    @QtCore.pyqtSlot()
    def viewReplay(self):
        if self.name in client.instance.urls:
            fa.exe.replay(client.instance.urls[self.name])

    
    @QtCore.pyqtSlot()
    def joinInGame(self):
        if self.name in client.instance.urls:
            client.instance.joinGameFromURL(client.instance.urls[self.name])
    
    @QtCore.pyqtSlot()
    def invite(self):
        QtGui.QMessageBox.information(None, "Under Construction", "Sorry, this feature is undergoing changes right now. <br/><b>It'll be available soon.</b>")
