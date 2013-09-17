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

from games.gameitem import GameItem, GameItemDelegate
from coop.coopmapitem import CoopMapItem, CoopMapItemDelegate
from games.hostgamewidget import HostgameWidget
from games import logger
from fa import Faction
import random
import fa
import modvault



FormClass, BaseClass = util.loadUiType("coop/coop.ui")


class CoopWidget(FormClass, BaseClass):
    def __init__(self, client, *args, **kwargs):
        
        BaseClass.__init__(self, *args, **kwargs)        
        
        self.setupUi(self)

        self.client = client
        self.client.coopTab.layout().addWidget(self)
        
        #Dictionary containing our actual games.
        self.games = {}
        
        #Ranked search UI
        self.ispassworded = False
        self.loaded = False
        
        self.coop = {}
        self.cooptypes = {}
        
        self.canChooseMap = False
        self.options = []
        
        self.client.showCoop.connect(self.coopChanged)
        self.client.coopInfo.connect(self.processCoopInfo)
        self.client.gameInfo.connect(self.processGameInfo)
        self.coopList.header().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        self.coopList.setItemDelegate(CoopMapItemDelegate(self))
        
        
        self.gameList.setItemDelegate(GameItemDelegate(self))
        self.gameList.itemDoubleClicked.connect(self.gameDoubleClicked)

        self.coopList.itemDoubleClicked.connect(self.coopListDoubleClicked)
        
        #Load game name from settings (yay, it's persistent!)        
        self.loadGameName()
        self.loadPassword()




    def coopChanged(self):
        if not self.loaded:
            self.client.send(dict(command="coop_list"))
            self.loaded = True


    def coopListDoubleClicked(self, item):
        '''
        Hosting a coop event
        '''
        if not hasattr(item, "mapUrl") :
            return
        
        if not fa.exe.available():
            return
            
        self.client.games.stopSearchRanked()
        self.gamemap = fa.maps.link2name(item.mapUrl)
        
        fa.exe.checkMap(self.gamemap, force=True)
        
        # A simple Hosting dialog.
        if fa.exe.check("coop"):     
            hostgamewidget = HostgameWidget(self, item)
            
            if hostgamewidget.exec_() == 1 :
                if self.gamename:
                    gameoptions = []
                    
                    if len(self.options) != 0 :
                        oneChecked = False
                        for option in self.options :
                            if option.isChecked() :
                                oneChecked = True
                            gameoptions.append(option.isChecked())
            
                        if oneChecked == False :
                            QtGui.QMessageBox.warning(None, "No option checked !", "You have to check at least one option !")
                            return
                    modnames = [str(moditem.text()) for moditem in hostgamewidget.modList.selectedItems()]
                    mods = [hostgamewidget.mods[modstr] for modstr in modnames]
                    modvault.setActiveMods(mods, True) #should be removed later as it should be managed by the server.
#                #Send a message to the server with our intent.
                    if self.ispassworded:
                        self.client.send(dict(command="game_host", access="password", password = self.gamepassword, mod=item.mod, title=self.gamename, mapname=self.gamemap, gameport=self.client.gamePort, options = gameoptions))
                    else :
                        self.client.send(dict(command="game_host", access="public", mod=item.mod, title=self.gamename, mapname=self.gamemap, gameport=self.client.gamePort, options = gameoptions))


    @QtCore.pyqtSlot(dict)
    def processCoopInfo(self, message): 
        '''
        Slot that interprets and propagates coop_info messages into the coop list 
        ''' 
        uid = message["uid"]
      
        
        if uid not in self.coop:
            typeCoop = message["type"]
            
            if not typeCoop in self.cooptypes:
                root_item = QtGui.QTreeWidgetItem()
                self.coopList.addTopLevelItem(root_item)
                root_item.setText(0, "<font color='white' size=+3>%s</font>" % typeCoop)
                self.cooptypes[typeCoop] = root_item
                root_item.setExpanded(True)
            else:
                root_item = self.cooptypes[typeCoop] 
            
            itemCoop = CoopMapItem(uid, self)
            itemCoop.update(message)
            
            root_item.addChild(itemCoop)

            self.coop[uid] = itemCoop

            
    @QtCore.pyqtSlot(dict)
    def processGameInfo(self, message):
        '''
        Slot that interprets and propagates game_info messages into GameItems 
        '''
        uid = message["uid"]
        if message["featured_mod"] == "coop":
            if 'max_players' in  message:
                message["max_players"] = 4
            
            
            
            if uid not in self.games:
                self.games[uid] = GameItem(uid)
                self.gameList.addItem(self.games[uid])
                self.games[uid].update(message, self.client)
            else:
                self.games[uid].update(message, self.client)

            if message['state'] == "open":
                # force the display.
                self.games[uid].setHidden(False)    
    
        #Special case: removal of a game that has ended         
        if message['state'] == "closed":
            if uid in self.games:
                self.gameList.takeItem(self.gameList.row(self.games[uid]))
                del self.games[uid]    
            return

        
    
    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def gameDoubleClicked(self, item):
        '''
        Slot that attempts to join a game.
        '''
        if not fa.exe.available():            
            return
        
        passw = None 
        
        if fa.exe.check(item.mod, item.mapname, None, item.mods):
            if item.access == "password" : 
                passw, ok = QtGui.QInputDialog.getText(self.client, "Passworded game" , "Enter password :", QtGui.QLineEdit.Normal, "")
                if ok:
                    self.client.send(dict(command="game_join", password=passw, uid=item.uid, gameport=self.client.gamePort))
            else :
                self.client.send(dict(command="game_join", uid=item.uid, gameport=self.client.gamePort))
                
        else:
            pass #checkFA failed and notified the user what was wrong. We won't join now.

    def savePassword(self, password):
        self.gamepassword = password
        util.settings.beginGroup("fa.games")
        util.settings.setValue("password", self.gamepassword)        
        util.settings.endGroup()        
                
                
    def loadPassword(self):
        util.settings.beginGroup("fa.games")
        self.gamepassword = util.settings.value("password", None)        
        util.settings.endGroup()        
                
        #Default Game Map ...
        if not self.gamepassword:
            self.gamepassword = "password"

    def saveGameMap(self, name):
        pass
                

    def saveGameName(self, name):
        self.gamename = name
        
        util.settings.beginGroup("fa.games")
        util.settings.setValue("gamename", self.gamename)        
        util.settings.endGroup()        
                
                
    def loadGameName(self):
        util.settings.beginGroup("fa.games")
        self.gamename = util.settings.value("gamename", None)        
        util.settings.endGroup()        
                
        #Default Game Name ...
        if not self.gamename:
            if (self.client.login):
                self.gamename = self.client.login + "'s game"
            else:
                self.gamename = "nobody's game"
        
