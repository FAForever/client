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





import random

from PyQt4 import QtCore, QtGui

import util
from games.gameitem import GameItem, GameItemDelegate
from games.moditem import ModItem, mod_invisible, mods
from games.hostgamewidget import HostgameWidget
from games._mapSelectWidget import mapSelectWidget
from fa import faction
import fa
import modvault
import notificatation_system as ns

import logging
logger = logging.getLogger(__name__)

RANKED_SEARCH_EXPANSION_TIME = 10000 #milliseconds before search radius expands

SEARCH_RADIUS_INCREMENT = 0.05
SEARCH_RADIUS_MAX = 0.25

FormClass, BaseClass = util.loadUiType("games/games.ui")

import functools


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
        self.canChooseMap = True


        self.teamFrame.setVisible(False)
        # Team search UI
        # self.teamAeon.setIcon(util.icon("games/automatch/aeon.png"))
        # self.teamCybran.setIcon(util.icon("games/automatch/cybran.png"))
        # self.teamSeraphim.setIcon(util.icon("games/automatch/seraphim.png"))
        # self.teamUEF.setIcon(util.icon("games/automatch/uef.png"))
        # self.teamRandom.setIcon(util.icon("games/automatch/random.png"))

        #self.teamRandom.setChecked(True)

        # self.connectTeamFactionToggles()

        # self.teamSearchButton={}
        # self.teamSearchButton[2] = self.players2
        # self.teamSearchButton[3] = self.players3
        # self.teamSearchButton[4] = self.players4
        # self.teamSearchButton[5] = self.players5
        # self.teamSearchButton[6] = self.players6

        # self.teamSearchFnc = {}

        # self.connectTeamSearchToggles()

        # self.teamTimer = QtCore.QTimer()
        # self.teamTimer.timeout.connect(self.expandSearchTeamRanked)
        # self.teamSearchProgress.hide()

        # self.client.matchmakerInfo.connect(self.handleMatchmakerInfo)

        # # Team search state variables
        # self.teamSearching = False

        # self.teamInvitations = {}

        self.client.modInfo.connect(self.processModInfo)
        self.client.gameInfo.connect(self.processGameInfo)

        self.client.rankedGameAeon.connect(self.togglingAeon)
        self.client.rankedGameCybran.connect(self.togglingCybran)
        self.client.rankedGameSeraphim.connect(self.togglingSeraphim)
        self.client.rankedGameUEF.connect(self.togglingUEF)
        self.client.rankedGameRandom.connect(self.togglingRandom)


        self.client.teamInvitation.connect(self.handleInvitations)
        self.client.teamInfo.connect(self.handleTeamInfo)


        self.client.gameEnter.connect(self.stopSearchRanked)
        self.client.viewingReplay.connect(self.stopSearchRanked)

        self.gameList.setItemDelegate(GameItemDelegate(self))
        self.gameList.itemDoubleClicked.connect(self.gameDoubleClicked)

        self.modList.itemDoubleClicked.connect(self.hostGameClicked)

        self.mapSelectButton.clicked.connect(self.mapSelectClicked)

        #self.TeamMapSelectButton.setVisible(False)

        # try:            
        #     self.teamInvitationsListWidget.itemDoubleClicked.connect(self.teamInvitationClicked)
        #     self.leaveTeamButton.clicked.connect(self.quitTeam)    
        #     self.leaveTeamButton.setVisible(False)
        # except:
        #     QtGui.QMessageBox.warning(None, "Skin outdated.", "The theme you are using is outdated. Please remove it or the lobby will malfunction.")

        #Load game name from settings (yay, it's persistent!)
        self.loadGameName()
        self.loadGameMap()
        self.loadPassword()
        self.options = []


    def handleMatchmakerInfo(self, message):
        action = message["action"]
        if action == "startSearching":
            if (not fa.check.check("matchmaker")):
                logger.error("Can't play ranked without successfully updating Forged Alliance.")
                return            

            self.client.send(dict(command="game_matchmaking", mod="matchmaker", state="port", port=self.client.gamePort))

            if self.client.useUPnP:
                fa.upnp.createPortMapping(self.client.localIP, self.client.gamePort, "UDP")

            numplayers = message["players"]

            self.disconnectTeamSearchToggles()
            for numplayer in self.teamSearchButton:
                if numplayer != numplayers:
                    self.teamSearchButton[numplayer].setChecked(False)
                else:
                    self.teamSearchButton[numplayer].setChecked(True)
            self.connectTeamSearchToggles()

            self.teamSearching = True
            self.teamSearchProgress.show()
        
        elif action == "stopSearching":
            self.teamSearching = False
            self.teamSearchProgress.hide()



    def handleTeamInfo(self, message):
        ''' handling team informations '''
        self.teamManagerListWidget.clear()

        if len(message["members"]) > 0:
            # cleaning invitations
            self.teamInvitationsListWidget.clear()
            self.leaveTeamButton.setVisible(True)

        else:
            self.leaveTeamButton.setVisible(False)

        for member in message["members"]:
            self.teamManagerListWidget.addItem(member)


    def handleInvitations(self, message):
        action  = message["action"]
        who     = message["who"]
        ''' handling team invitations '''     
        if action == "teaminvitationremove":
            if not who in self.teaminvitations:
                return
            
            self.teamInvitationsListWidget.removeItemWidget(self.teaminvitations[who])
            del self.teaminvitations[who]

        elif action == "teaminvitation":
            if who in self.teamInvitations:
                return

            if self.client.teaminvitations :
                self.client.forwardLocalBroadcast(who, "is inviting you to join his team.")

            self.client.notificationSystem.on_event(ns.NotificationSystem.TEAM_INVITE, "%s is inviting you to join his team." % who)

            item = QtGui.QListWidgetItem(who)
            
            self.teamInvitations[who] = item
            self.teamInvitationsListWidget.addItem(self.teamInvitations[who])

    def quitTeam(self):
        ''' leave a team '''
        self.client.send(dict(command="quit_team"))

    def teamInvitationClicked(self, item):
        ''' invitation acceptation '''
        who = item.text()
        self.client.send(dict(command="game_matchmaking", mod="matchmaker", state="port", port=self.client.gamePort))
        self.client.send(dict(command="accept_team_proposal", leader=who))


    def connectTeamFactionToggles(self):
        self.teamAeon.toggled.connect(self.togglingTeamAeon)
        self.teamCybran.toggled.connect(self.togglingTeamCybran)
        self.teamSeraphim.toggled.connect(self.togglingTeamSeraphim)
        self.teamUEF.toggled.connect(self.togglingTeamUEF)
        self.teamRandom.toggled.connect(self.togglingTeamRandom)        

    def disconnectTeamFactionToggles(self):
        self.teamAeon.toggled.disconnect(self.togglingTeamAeon)
        self.teamCybran.toggled.disconnect(self.togglingTeamCybran)
        self.teamSeraphim.toggled.disconnect(self.togglingTeamSeraphim)
        self.teamUEF.toggled.disconnect(self.togglingTeamUEF)
        self.teamRandom.toggled.disconnect(self.togglingTeamRandom) 


    def connectTeamSearchToggles(self):
        for numplayers in self.teamSearchButton:
            self.teamSearchFnc[numplayers] = functools.partial(self.togglingTeams, numplayers)
            self.teamSearchButton[numplayers].toggled.connect(self.teamSearchFnc[numplayers])
       

    def disconnectTeamSearchToggles(self):
        for numplayers in self.teamSearchButton:
            self.teamSearchButton[numplayers].toggled.disconnect(self.teamSearchFnc[numplayers])

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


    def mapSelectClicked(self):
        ''' This is for handling map selector'''
        mapSelection = mapSelectWidget(self)
        mapSelection.exec_()


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

            if message['state'] == 'open' and message['access'] == 'public':
                self.client.notificationSystem.on_event(ns.NotificationSystem.NEW_GAME, message)
        else:
            self.games[uid].update(message, self.client)


        #Special case: removal of a game that has ended
        if message['state'] == "closed":
            if uid in self.games:
                self.gameList.takeItem(self.gameList.row(self.games[uid]))
                del self.games[uid]
            return


    def startSearchingTeamMatchmaker(self, players):

        self.client.send(dict(command="game_matchmaking", mod="matchmaker", state="askingtostart", players=players, port=self.client.gamePort))


    def stopSearchingTeamMatchmaker(self):
        self.client.send(dict(command="game_matchmaking", mod="matchmaker", state="askingtostop"))
        #self.stopSearchRanked()



    def startSearchRanked(self, race):
        self.stopSearchingTeamMatchmaker()
        if fa.instance.running():
            QtGui.QMessageBox.information(None, "ForgedAllianceForever.exe", "FA is already running.")
            self.stopSearchRanked()
            return

        if (not fa.check.check("ladder1v1")):
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
    def expandSearchTeamRanked(self):
        self.radius += SEARCH_RADIUS_INCREMENT
        if self.radius >= SEARCH_RADIUS_MAX:
            self.radius = SEARCH_RADIUS_MAX;
            logger.debug("Search Team Cap reached at " + str(self.radius))
            self.rankedTimer.stop()
        else:
            logger.debug("Expanding teamsearch to " + str(self.radius))

        #self.client.send(dict(command="game_matchmaking", mod="ladder1v1", state="expand", rate=self.radius))


    @QtCore.pyqtSlot()
    def expandSearchRanked(self):
        self.radius += SEARCH_RADIUS_INCREMENT
        if self.radius >= SEARCH_RADIUS_MAX:
            self.radius = SEARCH_RADIUS_MAX;
            logger.debug("Search Cap reached at " + str(self.radius))
            self.teamTimer.stop()
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
    def togglingTeamAeon(self, state):
        self.toggleTeamAeon(1)

    @QtCore.pyqtSlot(bool)
    def togglingTeamCybran(self, state):
        self.toggleTeamCybran(1)


    @QtCore.pyqtSlot(bool)
    def togglingTeamSeraphim(self, state):
        self.toggleTeamSeraphim(1)

    @QtCore.pyqtSlot(bool)
    def togglingTeamRandom(self, state):
        self.toggleTeamRandom(1)

    @QtCore.pyqtSlot(bool)
    def togglingTeamUEF(self, state):
        self.toggleTeamUEF(1)

    @QtCore.pyqtSlot(bool)
    def toggleTeamUEF(self, state):
        if (state):
            self.disconnectTeamFactionToggles()
            self.teamAeon.setChecked(False)
            self.teamCybran.setChecked(False)
            self.teamSeraphim.setChecked(False)
            self.teamRandom.setChecked(False)
            self.connectTeamFactionToggles()
            self.client.send(dict(command="game_matchmaking", mod="matchmaker", state="faction", factionchosen=1))

    @QtCore.pyqtSlot(bool)
    def toggleTeamAeon(self, state):
        if (state):
            self.disconnectTeamFactionToggles()
            self.teamCybran.setChecked(False)
            self.teamSeraphim.setChecked(False)
            self.teamUEF.setChecked(False)
            self.teamRandom.setChecked(False)
            self.connectTeamFactionToggles()
            self.client.send(dict(command="game_matchmaking", mod="matchmaker", state="faction", factionchosen=2))



    @QtCore.pyqtSlot(bool)
    def toggleTeamCybran(self, state):
        if (state):
            self.disconnectTeamFactionToggles()
            self.teamAeon.setChecked(False)
            self.teamSeraphim.setChecked(False)
            self.teamUEF.setChecked(False)
            self.teamRandom.setChecked(False)
            self.connectTeamFactionToggles()
            self.client.send(dict(command="game_matchmaking", mod="matchmaker", state="faction", factionchosen=3))


    @QtCore.pyqtSlot(bool)
    def toggleTeamSeraphim(self, state):
        if (state):
            self.disconnectTeamFactionToggles()
            self.teamAeon.setChecked(False)
            self.teamCybran.setChecked(False)
            self.teamUEF.setChecked(False)
            self.teamRandom.setChecked(False)
            self.connectTeamFactionToggles()
            self.client.send(dict(command="game_matchmaking", mod="matchmaker", state="faction", factionchosen=4))

    @QtCore.pyqtSlot(bool)
    def toggleTeamRandom(self, state):
        if (state):
            self.disconnectTeamFactionToggles()
            self.teamAeon.setChecked(False)
            self.teamCybran.setChecked(False)
            self.teamSeraphim.setChecked(False)
            self.teamUEF.setChecked(False)
            self.connectTeamFactionToggles()
            self.client.send(dict(command="game_matchmaking", mod="matchmaker", state="faction", factionchosen=random.randint(1,4)))

    # TEAM MATCHMAKER
    @QtCore.pyqtSlot(bool)
    def togglingTeams(self, numplayers, state):
        if (state):
            self.startSearchingTeamMatchmaker(numplayers)
            self.disconnectTeamSearchToggles()
            for numplayer in self.teamSearchButton:
                if numplayer != numplayers:
                    self.teamSearchButton[numplayer].setChecked(False)
            self.connectTeamSearchToggles()
            
        else:
            self.stopSearchingTeamMatchmaker()
                                             

    # RANKED

    @QtCore.pyqtSlot(bool)
    def togglingAeon(self, state):
        self.client.rankedAeon.setChecked(1)
        self.toggleAeon(1)

    @QtCore.pyqtSlot(bool)
    def togglingCybran(self, state):
        self.client.rankedCybran.setChecked(1)
        self.toggleCybran(1)


    @QtCore.pyqtSlot(bool)
    def togglingSeraphim(self, state):
        self.client.rankedSeraphim.setChecked(1)
        self.toggleSeraphim(1)

    @QtCore.pyqtSlot(bool)
    def togglingRandom(self, state):
        self.client.rankedRandom.setChecked(1)
        self.toggleRandom(1)

    @QtCore.pyqtSlot(bool)
    def togglingUEF(self, state):
        self.client.rankedUEF.setChecked(1)
        self.toggleUEF(1)

    @QtCore.pyqtSlot(bool)
    def toggleUEF(self, state):
        if (state):
            self.startSearchRanked(faction.UEF)
            self.disconnectRankedToggles()
            self.rankedAeon.setChecked(False)
            self.rankedCybran.setChecked(False)
            self.rankedSeraphim.setChecked(False)
            self.rankedRandom.setChecked(False)
            self.connectRankedToggles()
        else:
            self.stopSearchRanked()

    @QtCore.pyqtSlot(bool)
    def toggleAeon(self, state):
        if (state):
            self.startSearchRanked(faction.AEON)
            self.disconnectRankedToggles()
            self.rankedCybran.setChecked(False)
            self.rankedSeraphim.setChecked(False)
            self.rankedUEF.setChecked(False)
            self.rankedRandom.setChecked(False)
            self.connectRankedToggles()
        else:
            self.stopSearchRanked()


    @QtCore.pyqtSlot(bool)
    def toggleCybran(self, state):
        if (state):
            self.startSearchRanked(faction.CYBRAN)
            self.disconnectRankedToggles()
            self.rankedAeon.setChecked(False)
            self.rankedSeraphim.setChecked(False)
            self.rankedUEF.setChecked(False)
            self.rankedRandom.setChecked(False)
            self.connectRankedToggles()
        else:
            self.stopSearchRanked()


    @QtCore.pyqtSlot(bool)
    def toggleSeraphim(self, state):
        if (state):
            self.startSearchRanked(faction.SERAPHIM)
            self.disconnectRankedToggles()
            self.rankedAeon.setChecked(False)
            self.rankedCybran.setChecked(False)
            self.rankedUEF.setChecked(False)
            self.rankedRandom.setChecked(False)
            self.connectRankedToggles()
        else:
            self.stopSearchRanked()

    @QtCore.pyqtSlot(bool)
    def toggleRandom(self, state):
        if (state):
            faction = random.randint(1,4)
            if faction == 1 :
                self.startSearchRanked(faction.UEF)
            elif faction == 2 :
                self.startSearchRanked(faction.CYBRAN)
            elif faction == 3 :
                self.startSearchRanked(faction.AEON)
            else :
                self.startSearchRanked(faction.SERAPHIM)

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
        if not fa.instance.available():
            return

        self.stopSearchRanked() #Actually a workaround

        passw = None

        if fa.check.check(item.mod, item.mapname, None, item.mods):
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
        if not fa.instance.available():
            return

        self.stopSearchRanked()

        # A simple Hosting dialog.
        if fa.check.check(item.mod):
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

