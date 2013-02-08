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
from games.moditem import ModItem, mod_invisible, mods
from games.hostgamewidget import HostgameWidget
from games import logger
from fa import Faction
import random
import fa

RANKED_SEARCH_EXPANSION_TIME = 10000 #milliseconds before search radius expands

SEARCH_RADIUS_INCREMENT = 0.05
SEARCH_RADIUS_MAX = 0.25

FormClass, BaseClass = util.loadUiType("games/games.ui")


class GamesWidget(FormClass, BaseClass):
    def __init__(self, client, *args, **kwargs):
        
        BaseClass.__init__(self, *args, **kwargs)        
        
        self.setupUi(self)

        self.client = client
        self.client.gamesTab.layout().addWidget(self)
        
        #Dictionary containing our actual games.
        self.games = {}
        
        #Ranked search UI
        self.rankedAeon.setIcon(util.icon("games/automatch/aeon.png"))
        self.rankedCybran.setIcon(util.icon("games/automatch/cybran.png"))
        self.rankedSeraphim.setIcon(util.icon("games/automatch/seraphim.png"))
        self.rankedUEF.setIcon(util.icon("games/automatch/uef.png"))
        self.rankedRandom.setIcon(util.icon("games/automatch/random.png"))


        self.connectRankedToggles()
        self.rankedTimer = QtCore.QTimer()
        self.rankedTimer.timeout.connect(self.expandSearchRanked)
        self.searchProgress.hide()

        # Ranked search state variables
        self.searching = False
        self.radius = 0
        self.race = None
        self.ispassworded = False
        
        self.client.modInfo.connect(self.processModInfo)
        self.client.gameInfo.connect(self.processGameInfo)
                
        self.client.gameEnter.connect(self.stopSearchRanked)
        self.client.viewingReplay.connect(self.stopSearchRanked)
        
        self.gameList.setItemDelegate(GameItemDelegate(self));
        self.gameList.itemDoubleClicked.connect(self.gameDoubleClicked)

        self.modList.itemDoubleClicked.connect(self.hostGameClicked)

        #Load game name from settings (yay, it's persistent!)        
        self.loadGameName()
        self.loadGameMap()
        self.loadPassword()
        self.options = []

    
    
    def connectRankedToggles(self):
        self.rankedAeon.toggled.connect(self.toggleAeon)
        self.rankedCybran.toggled.connect(self.toggleCybran)
        self.rankedSeraphim.toggled.connect(self.toggleSeraphim)
        self.rankedUEF.toggled.connect(self.toggleUEF)
        self.rankedRandom.toggled.connect(self.toggleRandom)



    def disconnectRankedToggles(self):
        self.rankedAeon.toggled.disconnect(self.toggleAeon)
        self.rankedCybran.toggled.disconnect(self.toggleCybran)
        self.rankedSeraphim.toggled.disconnect(self.toggleSeraphim)
        self.rankedUEF.toggled.disconnect(self.toggleUEF)
        self.rankedRandom.toggled.disconnect(self.toggleRandom)


    @QtCore.pyqtSlot(dict)
    def processModInfo(self, message): 
        '''
        Slot that interprets and propagates mod_info messages into the mod list 
        ''' 
        
        item = ModItem(message)
        
        if message["host"] :
            
            self.modList.addItem(item)       
        else :
            mod_invisible.append(message["name"])

        if not message["name"] in mods :
            mods[message["name"]] = item
            
        
        self.client.replays.modList.addItem(message["name"])
            
    @QtCore.pyqtSlot(dict)
    def processGameInfo(self, message):
        '''
        Slot that interprets and propagates game_info messages into GameItems 
        '''
        uid = message["uid"]

        if uid not in self.games:
            self.games[uid] = GameItem(uid)
            self.gameList.addItem(self.games[uid])
            self.games[uid].update(message, self.client)
        else:
            self.games[uid].update(message, self.client)


        #Special case: removal of a game that has ended         
        if message['state'] == "closed":
            if uid in self.games:
                self.gameList.takeItem(self.gameList.row(self.games[uid]))
                del self.games[uid]    
            return
        
                    
            

    def startSearchRanked(self, race):
        if (fa.exe.running()):
            QtGui.QMessageBox.information(None, "ForgedAlliance.exe", "FA is already running.")
            self.stopSearchRanked()
            return

        if (not fa.exe.check("ladder1v1")):
            self.stopSearchRanked()
            logger.error("Can't play ranked without successfully updating Forged Alliance.")
            return
        
        if (self.searching):
            logger.info("Switching Ranked Search to Race " + str(race))
            self.race = race
            self.client.send(dict(command="game_matchmaking", mod="ladder1v1", state="settings", faction = self.race))
        else:
            #Experimental UPnP Mapper - mappings are removed on app exit
            if self.client.useUPnP:
                fa.upnp.createPortMapping(self.client.localIP, self.client.gamePort, "UDP")
                
            logger.info("Starting Ranked Search as " + str(race) + ", port: " + str(self.client.gamePort))
            self.searching = True
            self.race = race
            self.radius = 0
            self.searchProgress.setVisible(True)
            self.labelAutomatch.setText("Searching...")
            self.rankedTimer.start(RANKED_SEARCH_EXPANSION_TIME)
            self.client.send(dict(command="game_matchmaking", mod="ladder1v1", state="start", gameport = self.client.gamePort, faction = self.race))
            #self.client.writeToServer('SEARCH_LADDERGAME', 'START', self.client.gamePort)

            
    @QtCore.pyqtSlot()
    def expandSearchRanked(self):
        self.radius += SEARCH_RADIUS_INCREMENT
        if self.radius >= SEARCH_RADIUS_MAX:
            self.radius = SEARCH_RADIUS_MAX;
            logger.debug("Search Cap reached at " + str(self.radius))
            self.rankedTimer.stop()
        else:
            logger.debug("Expanding search to " + str(self.radius))
        
        self.client.send(dict(command="game_matchmaking", mod="ladder1v1", state="expand", rate=self.radius))
            
            
    @QtCore.pyqtSlot()
    def stopSearchRanked(self, *args):
        if (self.searching):
            logger.debug("Stopping Ranked Search")
            self.rankedTimer.stop()
            self.client.send(dict(command="game_matchmaking", mod="ladder1v1", state="stop"))          
            self.searching = False
        
        self.searchProgress.setVisible(False)
        self.labelAutomatch.setText("1 vs 1 Automatch")
        
        self.disconnectRankedToggles()
        self.rankedAeon.setChecked(False)
        self.rankedCybran.setChecked(False)
        self.rankedSeraphim.setChecked(False)
        self.rankedUEF.setChecked(False)
        self.connectRankedToggles()
        

            
    @QtCore.pyqtSlot(bool)
    def toggleAeon(self, state):
        if (state):
            self.startSearchRanked(Faction.AEON)
            self.disconnectRankedToggles()
            self.rankedCybran.setChecked(False)
            self.rankedSeraphim.setChecked(False)
            self.rankedUEF.setChecked(False)
            self.connectRankedToggles()            
        else:
            self.stopSearchRanked()

            
    @QtCore.pyqtSlot(bool)
    def toggleCybran(self, state):
        if (state):
            self.startSearchRanked(Faction.CYBRAN)
            self.disconnectRankedToggles()
            self.rankedAeon.setChecked(False)
            self.rankedSeraphim.setChecked(False)
            self.rankedUEF.setChecked(False)
            self.connectRankedToggles()            
        else:
            self.stopSearchRanked()
            
            
    @QtCore.pyqtSlot(bool)
    def toggleSeraphim(self, state):
        if (state):
            self.startSearchRanked(Faction.SERAPHIM)
            self.disconnectRankedToggles()
            self.rankedAeon.setChecked(False)
            self.rankedCybran.setChecked(False)
            self.rankedUEF.setChecked(False)
            self.connectRankedToggles()            
        else:
            self.stopSearchRanked()

    @QtCore.pyqtSlot(bool)
    def toggleRandom(self, state):
        if (state):
            faction = random.randint(1,4)
            if faction == 1 :
                self.startSearchRanked(Faction.UEF)
            elif faction == 2 :
                self.startSearchRanked(Faction.CYBRAN)
            elif faction == 3 :
                self.startSearchRanked(Faction.AEON)
            else :
                self.startSearchRanked(Faction.SERAPHIM)
                
            self.disconnectRankedToggles()
            self.rankedAeon.setChecked(False)
            self.rankedCybran.setChecked(False)
            self.rankedSeraphim.setChecked(False)
            self.connectRankedToggles()     
        else:
            self.stopSearchRanked()                        
            
    @QtCore.pyqtSlot(bool)
    def toggleUEF(self, state):
        if (state):
            self.startSearchRanked(Faction.UEF)
            self.disconnectRankedToggles()
            self.rankedAeon.setChecked(False)
            self.rankedCybran.setChecked(False)
            self.rankedSeraphim.setChecked(False)
            self.connectRankedToggles()            
        else:
            self.stopSearchRanked()

            
    
    
    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def gameDoubleClicked(self, item):
        '''
        Slot that attempts to join a game.
        '''
        if not fa.exe.available():            
            return
        
        self.stopSearchRanked() #Actually a workaround

        passw = None 
        
        if fa.exe.check(item.mod, item.mapname):
            if item.access == "password" :                
                passw, ok = QtGui.QInputDialog.getText(self.client, "Passworded game" , "Enter password :", QtGui.QLineEdit.Normal, "")
                if ok:
                    self.client.send(dict(command="game_join", password=passw, uid=item.uid, gameport=self.client.gamePort))
            else :
                self.client.send(dict(command="game_join", uid=item.uid, gameport=self.client.gamePort))
                
        else:
            pass #checkFA failed and notified the user what was wrong. We won't join now.



    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def hostGameClicked(self, item):
        '''
        Hosting a game event
        '''
        if not fa.exe.available():
            return
            
        self.stopSearchRanked()
        
        # A simple Hosting dialog.
        if fa.exe.check(item.mod):     
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
#                #Send a message to the server with our intent.
                    if self.ispassworded :
                        self.client.send(dict(command="game_host", access="password", password = self.gamepassword, mod=item.mod, title=self.gamename, mapname=self.gamemap, gameport=self.client.gamePort, options = gameoptions))
                    else :
                        self.client.send(dict(command="game_host", access="public", mod=item.mod, title=self.gamename, mapname=self.gamemap, gameport=self.client.gamePort, options = gameoptions))
#

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
        self.gamemap = name
        util.settings.beginGroup("fa.games")
        util.settings.setValue("gamemap", self.gamemap)        
        util.settings.endGroup()        
                
                
    def loadGameMap(self):
        util.settings.beginGroup("fa.games")
        self.gamemap = util.settings.value("gamemap", None)        
        util.settings.endGroup()        
                
        #Default Game Map ...
        if not self.gamemap:
            self.gamemap = "scmp_007"


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
        
