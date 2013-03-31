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





'''
Created on Dec 1, 2011

@author: thygrrr
'''

from PyQt4 import QtCore, QtGui, QtNetwork, QtWebKit
from types import IntType, FloatType, ListType, DictType

from client import logger, ClientState, MUMBLE_URL, WEBSITE_URL, WIKI_URL,\
    FORUMS_URL, UNITDB_URL, SUPPORT_URL, TICKET_URL, GAME_PORT_DEFAULT, LOBBY_HOST,\
    LOBBY_PORT, LOCAL_REPLAY_PORT

import util
import fa

import json
import sys
import replays
import time
import os

from profile import playerstats

class ClientOutdated(StandardError):
    pass


FormClass, BaseClass = util.loadUiType("client/client.ui")

class ClientWindow(FormClass, BaseClass):
    '''
    This is the main lobby client that manages the FAF-related connection and data,
    in particular players, games, ranking, etc.
    Its UI also houses all the other UIs for the sub-modules.
    '''
    #These signals are emitted when the client is connected or disconnected from FAF
    connected    = QtCore.pyqtSignal()
    disconnected = QtCore.pyqtSignal()
    
    #This signal is emitted when the client is done rezising
    doneresize   = QtCore.pyqtSignal()
    
    #These signals notify connected modules of game state changes (i.e. reasons why FA is launched)
    viewingReplay = QtCore.pyqtSignal(QtCore.QUrl)
    
    #Game state controls
    gameEnter   = QtCore.pyqtSignal()
    gameExit    = QtCore.pyqtSignal()
     

     
    #These signals propagate important client state changes to other modules
    statsInfo           = QtCore.pyqtSignal(dict)
    tourneyTypesInfo    = QtCore.pyqtSignal(dict)
    tutorialsInfo       = QtCore.pyqtSignal(dict)
    tourneyInfo         = QtCore.pyqtSignal(dict)
    modInfo             = QtCore.pyqtSignal(dict)
    gameInfo            = QtCore.pyqtSignal(dict)   
    newGame             = QtCore.pyqtSignal(str)
    avatarList          = QtCore.pyqtSignal(list)
    playerAvatarList    = QtCore.pyqtSignal(dict)
    usersUpdated        = QtCore.pyqtSignal(list)
    localBroadcast      = QtCore.pyqtSignal(str, str)
    publicBroadcast     = QtCore.pyqtSignal(str)
    autoJoin            = QtCore.pyqtSignal(list)
    featuredModManager  = QtCore.pyqtSignal(str)
    featuredModManagerInfo = QtCore.pyqtSignal(dict)
    replayVault         = QtCore.pyqtSignal(dict) 

    #These signals are emitted whenever a certain tab is activated
    showReplays     = QtCore.pyqtSignal()
    showMaps        = QtCore.pyqtSignal()
    showGames       = QtCore.pyqtSignal()
    showTourneys    = QtCore.pyqtSignal()
    showLadder      = QtCore.pyqtSignal()
    showChat        = QtCore.pyqtSignal()    

    joinGameFromUser   = QtCore.pyqtSignal(str)
    joinReplayFromUser = QtCore.pyqtSignal(str)

    joinGameFromURL    = QtCore.pyqtSignal(str)
    joinReplayFromURL  = QtCore.pyqtSignal(str)
    
    
    def __init__(self, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)        
        
        logger.debug("Client instantiating")
        
        # Hook to Qt's application management system
        QtGui.QApplication.instance().aboutToQuit.connect(self.cleanup)
               
        #Init and wire the TCP Network socket to communicate with faforever.com
        self.socket = QtNetwork.QTcpSocket()
        self.socket.readyRead.connect(self.readFromServer)
        self.socket.disconnected.connect(self.disconnectedFromServer)
        self.socket.error.connect(self.socketError)
        self.blockSize = 0

        self.uniqueId = None
        self.udpTest = False
        self.profile = playerstats.Statpage(self)

        self.sendFile = False
        self.progress = QtGui.QProgressDialog()
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        
        #Tray icon
        self.tray = QtGui.QSystemTrayIcon()
        self.tray.setIcon(util.icon("client/tray_icon.png"))
        self.tray.show()
        
        self.state = ClientState.NONE
        self.session = None

        #Timer for resize events
        self.resizeTimer = QtCore.QTimer(self)
        self.resizeTimer.timeout.connect(self.resized)
        self.preferedSize = 0
               
        #Process used to run Forged Alliance (managed in module fa)
        fa.exe.instance.started.connect(self.startedFA)
        fa.exe.instance.finished.connect(self.finishedFA)
        self.gameInfo.connect(fa.exe.instance.processGameInfo)
        
        #Local Replay Server (and relay)
        self.replayServer = fa.replayserver.ReplayServer(self)
        
        #Local Relay Server
        self.relayServer = fa.relayserver.RelayServer(self)
        
        #Local proxy servers
        self.proxyServer = fa.proxies.proxies(self)
        
        #create user interface (main window) and load theme
        self.setupUi(self)
        self.setStyleSheet(util.readstylesheet("client/client.css"))
        self.setWindowTitle("FA Forever " + util.VERSION_STRING)

        #Wire all important signals
        self.mainTabs.currentChanged.connect(self.mainTabChanged)
        
        #Verrry important step!
        self.loadSettingsPrelogin()            

        self.players = {}       # Player names known to the client, contains the player_info messages sent by the server
        self.urls = {}          # user game location URLs - TODO: Should go in self.players
        
        self.friends = []       # names of the client's friends
        self.foes    = []       # names of the client's foes
                
        self.power = 0          # current user power        
               
        #Initialize the Menu Bar according to settings etc.
        self.initMenus()

        #Load the icons for the tabs
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.whatNewTab  ), util.icon("client/feed.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.chatTab     ), util.icon("client/chat.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.gamesTab    ), util.icon("client/games.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.mapsTab     ), util.icon("client/maps.png"))
        
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.ladderTab   ), util.icon("client/ladder.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.tourneyTab  ), util.icon("client/tourney.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.replaysTab  ), util.icon("client/replays.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.tutorialsTab), util.icon("client/tutorials.png"))
        
        QtWebKit.QWebSettings.globalSettings().setAttribute(QtWebKit.QWebSettings.PluginsEnabled, True)
        
        
        #for moderator 
        self.modMenu = None
        
        #self.mainTabs.setTabEnabled(self.mainTabs.indexOf(self.tourneyTab), False)
                
    def setup(self):
        import chat
        import tourneys
        import stats
        import vault
        import games
        import tutorials
        import featuredmods
        from chat._avatarWidget import avatarWidget
        
        
        # Initialize chat
        self.chat = chat.Lobby(self)
    
        #build main window with the now active client                  
        self.ladder = stats.Stats(self)
        self.games = games.Games(self)
        self.tourneys = tourneys.Tourneys(self)
        self.vault = vault.MapVault(self)
        self.replays = replays.Replays(self)
        self.tutorials = tutorials.Tutorials(self)
        
        # Other windows
        self.featuredMods = featuredmods.FeaturedMods(self)
        self.avatarAdmin  = self.avatarSelection = avatarWidget(self, None)



    @QtCore.pyqtSlot()
    def cleanup(self):
        '''
        Perform cleanup before the UI closes
        '''        
        self.state = ClientState.SHUTDOWN

        self.progress.setWindowTitle("FAF is shutting down")
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        self.progress.setValue(0)
        self.progress.setCancelButton(None)
        self.progress.show()
                
        #Important: If a game is running, offer to terminate it gently
        self.progress.setLabelText("Closing ForgedAlliance.exe")
        fa.exe.close()

        #Terminate Lobby Server connection
        if self.socket.state() == QtNetwork.QTcpSocket.ConnectedState:
            self.progress.setLabelText("Closing main connection.")
            self.socket.disconnectFromHost()
            
        # Terminate tournament connection
        if self.tourneys :
            self.progress.setLabelText("Closing tournament connection.")
            self.tourneys.tournamentSocket.disconnectFromHost()
        
        # Clear UPnP Mappings...
        if self.useUPnP:
            self.progress.setLabelText("Removing UPnP port mappings")
            fa.upnp.removePortMappings()

        #Terminate local ReplayServer
        if self.replayServer:
            self.progress.setLabelText("Terminating local replay server")
            self.replayServer.close()
            self.replayServer = None

        #Terminate local ReplayServer
        if self.relayServer:
            self.progress.setLabelText("Terminating local relay server")
            self.relayServer.close()
            self.relayServer = None
        
        #Clean up Chat
        if self.chat:
            self.progress.setLabelText("Disconnecting from IRC")
            self.chat.disconnect()
            self.chat = None
        
        # Get rid of the Tray icon        
        if self.tray:
            self.progress.setLabelText("Removing System Tray icon")
            self.tray.deleteLater()
            self.tray = None
                    
        #Terminate UI
        if self.isVisible():
            self.progress.setLabelText("Closing main window")
            self.close()

        self.progress.close()
        
        

    def closeEvent(self, event):
        logger.info("Close Event for Application Main Window")
        self.saveWindow()
        
        if (fa.exe.running()):
            if QtGui.QMessageBox.question(self, "Are you sure?", "Seems like you still have Forged Alliance running!<br/><b>Close anyway?</b>", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No) == QtGui.QMessageBox.No:
                event.ignore()
                return
        
        return QtGui.QMainWindow.closeEvent(self, event)
        

    def resizeEvent(self, size):
        self.resizeTimer.start(400)
        
    def resized(self):
        self.resizeTimer.stop()
        self.doneresize.emit()
     
    def initMenus(self):
        self.actionLinkMumble.triggered.connect(self.linkMumble)
        self.actionLinkWebsite.triggered.connect(self.linkWebsite)
        self.actionLinkWiki.triggered.connect(self.linkWiki)
        self.actionLinkForums.triggered.connect(self.linkForums)
        self.actionLinkUnitDB.triggered.connect(self.linkUnitDB)

        self.actionWiki.triggered.connect(self.linkWiki)
        self.actionReportBug.triggered.connect(self.linkReportBug)
        self.actionShowLogs.triggered.connect(self.linkShowLogs)
        self.actionTechSupport.triggered.connect(self.linkTechSupport)
        self.actionAbout.triggered.connect(self.linkAbout)
        
        
        self.actionClearCache.triggered.connect(self.clearCache)        
        self.actionClearSettings.triggered.connect(self.clearSettings)        
        self.actionClearGameFiles.triggered.connect(self.clearGameFiles)

        self.actionSetGamePath.triggered.connect(self.switchPath)
        self.actionSetGamePort.triggered.connect(self.switchPort)
        self.actionSetMumbleOptions.triggered.connect(self.setMumbleOptions)


        #Toggle-Options
        self.actionSetAutoLogin.triggered.connect(self.updateOptions)
        self.actionSetSoundEffects.triggered.connect(self.updateOptions)
        self.actionSetOpenGames.triggered.connect(self.updateOptions)
        self.actionSetJoinsParts.triggered.connect(self.updateOptions)
        self.actionSetLiveReplays.triggered.connect(self.updateOptions)
        self.actionSaveGamelogs.triggered.connect(self.updateOptions)
        self.actionActivateMumbleSwitching.triggered.connect(self.saveMumbleSwitching)
        
        
        #Init themes as actions.
        themes = util.listThemes()
        for theme in themes:
            action = self.menuTheme.addAction(str(theme))
            action.triggered.connect(self.switchTheme)
            action.theme = theme
            action.setCheckable(True)            
            
            if util.getTheme() == theme:
                action.setChecked(True)
        
        # Nice helper for the developers
        self.menuTheme.addSeparator()
        self.menuTheme.addAction("Reload Stylesheet", lambda: self.setStyleSheet(util.readstylesheet("client/client.css")))
        
        
        
    @QtCore.pyqtSlot()
    def updateOptions(self):
        self.autologin = self.actionSetAutoLogin.isChecked()
        self.soundeffects = self.actionSetSoundEffects.isChecked()
        self.opengames = self.actionSetOpenGames.isChecked()
        self.joinsparts = self.actionSetJoinsParts.isChecked()
        self.livereplays = self.actionSetLiveReplays.isChecked()
        self.gamelogs = self.actionSaveGamelogs.isChecked()
                 
        self.saveChat()
        self.saveCredentials()
        pass
    
    
    @QtCore.pyqtSlot()
    def switchTheme(self):
        util.setTheme(self.sender().theme, True)

        
    @QtCore.pyqtSlot()
    def switchPath(self):
        fa.updater.Wizard(self).exec_()
        
    @QtCore.pyqtSlot()
    def switchPort(self):
        import loginwizards
        loginwizards.gameSettingsWizard(self).exec_()
        
    @QtCore.pyqtSlot()
    def setMumbleOptions(self):
        import loginwizards
        loginwizards.mumbleOptionsWizard(self).exec_()
                
    @QtCore.pyqtSlot()
    def clearSettings(self):
        result = QtGui.QMessageBox.question(None, "Clear Settings", "Are you sure you wish to clear all settings, login info, etc. used by this program?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if (result == QtGui.QMessageBox.Yes):
                        
            util.settings.clear()
            util.settings.sync()
            QtGui.QMessageBox.information(None, "Restart Needed", "FAF will quit now.")
            QtGui.QApplication.quit()

    @QtCore.pyqtSlot()
    def clearGameFiles(self):
        util.clearDirectory(util.BIN_DIR)
        util.clearDirectory(util.GAMEDATA_DIR)   
    
    @QtCore.pyqtSlot()
    def clearCache(self):
        changed = util.clearDirectory(util.CACHE_DIR)
        if changed:
            QtGui.QMessageBox.information(None, "Restart Needed", "FAF will quit now.")
            QtGui.QApplication.quit()
        
    
    @QtCore.pyqtSlot()
    def linkMumble(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(MUMBLE_URL.format(login=self.login)))

    @QtCore.pyqtSlot()
    def linkWebsite(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(WEBSITE_URL))

    @QtCore.pyqtSlot()
    def linkWiki(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(WIKI_URL))

    @QtCore.pyqtSlot()
    def linkForums(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(FORUMS_URL))

    @QtCore.pyqtSlot()
    def linkUnitDB(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(UNITDB_URL))

    @QtCore.pyqtSlot()
    def linkReportBug(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(TICKET_URL))
        #from util.report import ReportDialog
        #ReportDialog(self).show()

    @QtCore.pyqtSlot()
    def linkTechSupport(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(SUPPORT_URL))

    @QtCore.pyqtSlot()
    def linkShowLogs(self):
        util.showInExplorer(util.LOG_DIR)
        
    @QtCore.pyqtSlot()
    def linkAbout(self):
        dialog = util.loadUi("client/about.ui")
        dialog.exec_()
        
        
    def saveCredentials(self):
        util.settings.beginGroup("user")
        util.settings.setValue("user/remember", self.remember) #always remember to remember
        if self.remember:            
            util.settings.setValue("user/login", self.login)
            util.settings.setValue("user/password", self.password)
            util.settings.setValue("user/autologin", self.autologin) #only autologin if remembering 
        else:
            util.settings.setValue("user/login", None)
            util.settings.setValue("user/password", None)
            util.settings.setValue("user/autologin", False)
        util.settings.endGroup()
        util.settings.sync()


    def clearAutologin(self):
        self.autologin = False
        self.actionSetAutoLogin.setChecked(False)
        
        util.settings.beginGroup("user")
        util.settings.setValue("user/autologin", False)
        util.settings.endGroup()
        util.settings.sync()
        

    def saveWindow(self):
        util.settings.beginGroup("window")
        util.settings.setValue("geometry", self.saveGeometry())
        util.settings.endGroup()        
        util.settings.beginGroup("ForgedAlliance")
        util.settings.setValue("app/falogs", self.gamelogs)
        util.settings.endGroup()
        
    def savePort(self):
        util.settings.beginGroup("ForgedAlliance")
        util.settings.setValue("app/gameport", self.gamePort)
        util.settings.setValue("app/upnp", self.useUPnP)
        
        util.settings.endGroup()
        util.settings.sync()
                
    def saveMumble(self):
        util.settings.beginGroup("Mumble")
        util.settings.setValue("app/mumble", self.enableMumble)
        util.settings.endGroup()
        util.settings.sync()

    def saveMumbleSwitching(self):
        self.activateMumbleSwitching = self.actionActivateMumbleSwitching.isChecked()

        util.settings.beginGroup("Mumble")
        util.settings.setValue("app/activateMumbleSwitching", self.activateMumbleSwitching)
        util.settings.endGroup()
        util.settings.sync()

    @QtCore.pyqtSlot()
    def saveChat(self):        
        util.settings.beginGroup("chat")
        util.settings.setValue("soundeffects", self.soundeffects)
        util.settings.setValue("livereplays", self.livereplays)
        util.settings.setValue("opengames", self.opengames)
        util.settings.setValue("joinsparts", self.joinsparts)
        util.settings.endGroup()
        
    
    def loadSettingsPrelogin(self):

        util.settings.beginGroup("user")
        self.login = util.settings.value("user/login")
        self.password = util.settings.value("user/password")
        self.remember = (util.settings.value("user/remember") == "true")
        
        # This is the new way we do things.
        self.autologin = (util.settings.value("user/autologin") == "true")
        self.actionSetAutoLogin.setChecked(self.autologin)        
        util.settings.endGroup()
        
        
       
    def loadSettings(self):
        #Load settings
        fa.loadPath()
                
        util.settings.beginGroup("window")
        geometry =  util.settings.value("geometry", None)
        if geometry:
            self.restoreGeometry(geometry)
        util.settings.endGroup()        
                
        util.settings.beginGroup("ForgedAlliance")
        self.gamePort = int(util.settings.value("app/gameport", GAME_PORT_DEFAULT))
        self.useUPnP = (util.settings.value("app/upnp", "false") == "true")
        self.gamelogs = (util.settings.value("app/falogs", "false") == "true")
        self.actionSaveGamelogs.setChecked(self.gamelogs)
        util.settings.endGroup()

        util.settings.beginGroup("Mumble")

        if util.settings.value("app/mumble", "firsttime") == "firsttime":
            # The user has never configured mumble before. Be a little intrusive and ask him if he wants to use it.
            if QtGui.QMessageBox.question(self, "Enable Voice Connector?", "FA Forever can connect with <a href=\"http://mumble.sourceforge.net/\">Mumble</a> to support the automatic setup of voice connections between you and your team mates. Would you like to enable this feature? You can change the setting at any time by going to options -> settings -> Voice", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes:
                util.settings.setValue("app/mumble", "true")
            else:
                util.settings.setValue("app/mumble", "false")

        if util.settings.value("app/activateMumbleSwitching", "firsttime") == "firsttime":
            util.settings.setValue("app/activateMumbleSwitching", "true")

        self.enableMumble = (util.settings.value("app/mumble", "false") == "true")
        self.activateMumbleSwitching = (util.settings.value("app/activateMumbleSwitching", "false") == "true")
        util.settings.endGroup()

        self.actionActivateMumbleSwitching.setChecked(self.activateMumbleSwitching)
               
        self.loadChat()
        
        
    def loadChat(self):        
        try:
            util.settings.beginGroup("chat")        
            self.soundeffects = (util.settings.value("soundeffects", "true") == "true")
            self.opengames = (util.settings.value("opengames", "true") == "true")
            self.joinsparts = (util.settings.value("joinsparts", "false") == "true")
            self.livereplays = (util.settings.value("livereplays", "true") == "true")
            util.settings.endGroup()

            self.actionSetSoundEffects.setChecked(self.soundeffects)
            self.actionSetLiveReplays.setChecked(self.livereplays)
            self.actionSetOpenGames.setChecked(self.opengames)
            self.actionSetJoinsParts.setChecked(self.joinsparts)
        except:
            pass

     
    def processTestGameportDatagram(self):
        self.udpTest = True
        
    def testGamePort(self):
        '''
        Here, we test with the server if the current game port set is all right.
        If not, we propose alternatives to the user
        '''
        if self.useUPnP:
            fa.upnp.createPortMapping(self.localIP, self.gamePort, "UDP")
        
        #binding the port
        udpSocket =  QtNetwork.QUdpSocket(self)
        udpSocket.bind(self.gamePort)
        udpSocket.readyRead.connect(self.processTestGameportDatagram)
        
        if udpSocket.localPort() != self.gamePort :
            logger.error("The game port set (%i) is not available." % self.gamePort)
            answer = QtGui.QMessageBox.warning(None, "Port Occupied", "FAF has detected that the gameport you choose is not available. Possible reasons:<ul><li><b>FAF is already running</b> (most likely)</li><li>another program is listening on port {port}</li></ul><br>If you click Apply, FAF will port {port2} for this session.".format(port=self.gamePort, port2 = udpSocket.localPort()), QtGui.QMessageBox.Apply, QtGui.QMessageBox.Abort)
            if answer == QtGui.QMessageBox.Apply:
                self.gamePort = udpSocket.localPort()
                
            else :
                udpSocket.close()
                udpSocket.deleteLater()
                return False
        logger.info("The game port is now set to %i" % self.gamePort)
        #now we try sending a packet to the server
        logger.info("sending packet to " + LOBBY_HOST)

        
        if udpSocket.writeDatagram(self.login, QtNetwork.QHostAddress(QtNetwork.QHostInfo.fromName(LOBBY_HOST ).addresses ()[0]), 30351) == -1 :
            logger.info("Unable to send UDP Packet")
            QtGui.QMessageBox.critical(self, "UDP Packet not sent !", "We are not able to send a UDP packet. <br><br>Possible reasons:<ul><li><b>Your firewall is blocking the UDP port {port}.</b></li><li><b>Your router is blocking or routing port {port} in a wrong way.</b></li></ul><br><font size='+2'>How to fix this : </font> <ul><li>Check your firewall and router. <b>More info in the wiki (Links -> Wiki)</li></b><li>You should also consider using <b>uPnP (Options -> Settings -> Gameport)</b></li><li>You should ask for assistance in the TechQuestions chat and/or in the <b>technical forum (Links -> Forums<b>)</li></ul><br><font size='+1'><b>FA will not be able to perform correctly until this issue is fixed.</b></font>".format(port=self.gamePort))
        
        
        
        self.progress.setCancelButtonText("Cancel")
        self.progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
        self.progress.setAutoClose(False)
        self.progress.setAutoReset(False)
        self.progress.setModal(1)
        self.progress.setWindowTitle("UDP test...")
        self.progress.setLabelText("We are waiting for an UDP answer from the server on port %i." % (self.gamePort))
        self.progress.show()        
        
        timer = time.time()
        interval = 1
        
        while self.udpTest == False :
            QtGui.QApplication.processEvents()
            if time.time() - timer > interval :
                udpSocket.writeDatagram(self.login, QtNetwork.QHostAddress("91.236.254.74"), 30351)
                interval = interval + 1

            if time.time() - timer > 10 :
                break

        self.progress.close()

        udpSocket.close()
        udpSocket.deleteLater()     
        
        if self.udpTest == False :
            logger.info("Unable to receive UDP Packet")
            QtGui.QMessageBox.critical(self, "UDP Packet not received !", "We didn't received any answer from the server. <br><br>Possible reasons:<ul><li><b>Your firewall is blocking the UDP port {port}.</b></li><li><b>Your router is blocking or routing port {port} in a wrong way/to the wrong computer.</b></li></ul><br><font size='+2'>How to fix this : </font> <ul><li>Check your firewall and router. <b>More info in the wiki (Links -> Wiki)</li></b><li>You should also consider using <b>uPnP (Options -> Settings -> Gameport)</b></li><li>You should ask for assistance in the TechQuestions chat and/or in the <b>technical forum (Links -> Forums<b>)</li></ul><br><font size='+1'><b>FA will not be able to perform correctly until this issue is fixed.</b></font>".format(port=self.gamePort))
        
        return True
    
    def doConnect(self):  
         
        if not self.replayServer.doListen(LOCAL_REPLAY_PORT):
            return False
        
        if not self.relayServer.doListen():
            return False

        self.progress.setCancelButtonText("Cancel")
        self.progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
        self.progress.setAutoClose(False)
        self.progress.setAutoReset(False)
        self.progress.setModal(1)
        self.progress.setWindowTitle("Connecting...")
        self.progress.setLabelText("Establishing connection ...")
        self.progress.show()                

        # Begin connecting.        
        self.socket.setSocketOption(QtNetwork.QTcpSocket.KeepAliveOption, 1)
        self.socket.connectToHost(LOBBY_HOST, LOBBY_PORT)
        
        
        
        while (self.socket.state() != QtNetwork.QAbstractSocket.ConnectedState) and self.progress.isVisible():
            QtGui.QApplication.processEvents()                                        

        self.state = ClientState.NONE    
        self.localIP = str(self.socket.localAddress().toString())
        

#        #Perform Version Check first        
        if not self.socket.state() == QtNetwork.QAbstractSocket.ConnectedState:
            
            self.progress.close() # in case it was still showing...
            # We either cancelled or had a TCP error, meaning the connection failed..
            if self.progress.wasCanceled():
                logger.warn("doConnect() aborted by user.")
            else:
                logger.error("doConnect() failed with clientstate " + str(self.state) + ", socket errorstring: " + self.socket.errorString())
            return False
        else:     
  
            return True       



    def waitSession(self):
        self.progress.setLabelText("Setting up Session...")
        self.send(dict(command="ask_session"))
        start = time.time()
        while self.session == None and self.progress.isVisible() :
            QtGui.QApplication.processEvents()
            if time.time() - start > 5 :
                break  
       
       
        if not self.session :
            if self.progress.wasCanceled():
                logger.warn("waitSession() aborted by user.")
            else :
                logger.error("waitSession() failed with clientstate " + str(self.state) + ", socket errorstring: " + self.socket.errorString())
                QtGui.QMessageBox.critical(self, "Notice from Server", "Unable to get a session : <br> Server under maintenance.<br><br>Please retry in some minutes.")
            return False
               
        self.uniqueId = util.uniqueID(self.login, self.session)
        self.loadSettings()

        #
        # Voice connector (This isn't supposed to be here, but I need the settings to be loaded before I can determine if we can hook in the mumbleConnector
        #
        if self.enableMumble:
            self.progress.setLabelText("Setting up Mumble...")
            import mumbleconnector
            self.mumbleConnector = mumbleconnector.MumbleConnector(self)
        return True  
        
    
    def doLogin(self):
        
        #Determine if a login wizard needs to be displayed and do so
        if not self.autologin or not self.password or not self.login:        
            import loginwizards
            if not loginwizards.LoginWizard(self).exec_():
                return False;
        
        self.progress.setLabelText("Logging in...")
        self.progress.reset()
        self.progress.show()                       
         
        self.login = self.login.strip()      
        logger.info("Attempting to login as: " + str(self.login))
        self.state = ClientState.NONE
        
        
        
        if not self.uniqueId :
            QtGui.QMessageBox.warning(QtGui.QApplication.activeWindow(), "Unable to login", "It seems that you miss some important DLL.<br>Please install :<br><a href =\"http://www.microsoft.com/download/en/confirmation.aspx?id=8328\">http://www.microsoft.com/download/en/confirmation.aspx?id=8328</a> and <a href = \"http://www.microsoft.com/en-us/download/details.aspx?id=17851\">http://www.microsoft.com/en-us/download/details.aspx?id=17851</a><br><br>You probably have to restart your computer after installing them.<br><br>Please visit this link in case of problems : <a href=\"http://www.faforever.com/forums/viewforum.php?f=3\">http://www.faforever.com/forums/viewforum.php?f=3</a>", QtGui.QMessageBox.Close)
            return False
        else :
            self.send(dict(command="hello", version=util.VERSION, login=self.login, password = self.password, unique_id = self.uniqueId, local_ip = self.localIP))
        
        while (not self.state) and self.progress.isVisible():
            QtGui.QApplication.processEvents()
            

        if self.progress.wasCanceled():
            logger.warn("Login aborted by user.")
            return False
        
        self.progress.close()


        
        if self.state == ClientState.OUTDATED :
                logger.warn("Client is OUTDATED.")

        elif self.state == ClientState.ACCEPTED:
            logger.info("Login accepted.")
           
            # update what's new page
            self.whatNewsView.setUrl(QtCore.QUrl("http://www.faforever.com/?page_id=114&username={user}&pwdhash={pwdhash}".format(user=self.login, pwdhash=self.password))) 
            # update tournament
            self.tourneys.updateTournaments()
            
            util.report.BUGREPORT_USER = self.login
            util.crash.CRASHREPORT_USER = self.login

            if not self.testGamePort() :
                return False

            #success: save login data (if requested) and carry on
            self.actionSetAutoLogin.setChecked(self.autologin)
            self.updateOptions()

            self.progress.close()                        
            #This is a triumph... I'm making a note here: Huge success!
            self.connected.emit()            
            return True            
        elif self.state == ClientState.REJECTED:
            logger.warning("Login rejected.")
            #seems that there isa bug in a key ..
            util.settings.beginGroup("window")
            util.settings.remove("geometry")
            util.settings.endGroup()        
            self.clearAutologin()
            return self.doLogin()   #Just try to login again, slightly hackish but I can get away with it here, I guess.
        else:
            # A more profound error has occurrect (cancellation or disconnection)
            return False




    def loginCreation(self, result):
        '''
        Simply acknowledges the answer the server gave to our account creation attempt,
        and sets the client's state accordingly so the Account Creation Wizard
        can continue its work.
        '''
        logger.debug("Account name free and valid: " + result)

        if result == "yes" :
            self.state = ClientState.CREATED
        else:
            self.state = ClientState.REJECTED


    def isFriend(self, name):
        '''
        Convenience function for other modules to inquire about a user's friendliness.
        '''
        return name in self.friends

    
    def isFoe(self, name):
        '''
        Convenience function for other modules to inquire about a user's foeliness.
        '''
        return name in self.foes

    def isPlayer(self, name):
        '''
        Convenience function for other modules to inquire about a user's civilian status.
        '''        
        return name in self.players or name == self.login



    #Color table used by the following method
    # CAVEAT: This will break if the theme is loaded after the client package is imported
    colors = json.loads(util.readfile("client/colors.json"))

    def getUserLeague(self, name):
        '''
        Returns a user's league if any
        '''        
        if name in self.players:
            if "league" in self.players[name] : 
                return self.players[name]["league"]
            

        return None
    
    def getUserCountry(self, name):
        '''
        Returns a user's country if any
        '''        
        if name in self.players:
            if "country" in self.players[name] : 
                return self.players[name]["country"]
            

        return None
    
    def getUserAvatar(self, name):
        '''
        Returns a user's avatar if any
        '''        
        if name in self.players:
            return self.players[name]["avatar"]
        else:
            return None
    
    
    def getUserColor(self, name):
        '''
        Returns a user's color depending on their status with relation to the FAF client
        '''
        if name == self.login:
            return self.getColor("self")
        elif name in self.friends:
            return self.getColor("friend")
        elif name in self.foes:
            return self.getColor("foe")
        elif name in self.players:
            return self.getColor("player")
        else:
            return self.getColor("default")


    def getColor(self, name):
        if name in self.colors:
            return self.colors[name]
        else:
            return self.colors["default"]

    
    
    def getUserRanking(self, name):
        '''
        Returns a user's ranking (trueskill rating) as a float.
        '''
        if name in self.players:
            return self.players[name]["rating_mean"] - 3*self.players[name]["rating_deviation"]
        else:
            return None



    @QtCore.pyqtSlot()
    def startedFA(self):
        '''
        Slot hooked up to fa.exe.instance when the process has launched.
        It will notify other modules through the signal gameEnter().
        '''
        logger.info("FA has launched in an attached process.")
        self.gameEnter.emit()


    @QtCore.pyqtSlot(int)
    def finishedFA(self, exit_code):
        '''
        Slot hooked up to fa.exe.instance when the process has ended.
        It will notify other modules through the signal gameExit().
        '''        
        if not exit_code:
            logger.info("FA has finished with exit code: " + str(exit_code))
        else:
            logger.warn("FA has finished with exit code: " + str(exit_code))
        
        self.writeToServer("FA_CLOSED")
        self.gameExit.emit()

        

    @QtCore.pyqtSlot(int)
    def mainTabChanged(self, index):
        '''
        The main visible tab (module) of the client's UI has changed.
        In this case, other modules may want to load some data or cease
        particularly CPU-intensive interactive functionality.
        LATER: This can be rewritten as a simple Signal that each module can then individually connect to.
        '''
        new_tab = self.mainTabs.widget(index)
        if new_tab is self.gamesTab:
            self.showGames.emit()

        if new_tab is self.mapsTab:
            self.showMaps.emit()

        if new_tab is self.chatTab:
            self.showChat.emit()

        if new_tab is self.replaysTab:
            self.showReplays.emit()

        if new_tab is self.ladderTab:
            self.showLadder.emit()

        if new_tab is self.tourneyTab:
            self.showTourneys.emit()

    def joinGameFromURL(self, url):
        '''
        Tries to join the game at the given URL
        '''
        logger.debug("joinGameFromURL: " + url.toString())
        if (fa.exe.available()):
            if fa.exe.check(url.queryItemValue("mod"), url.queryItemValue("map")):
                self.send(dict(command="game_join", uid=int(url.queryItemValue("uid")), gameport=self.gamePort))
    

    def loginWriteToFaServer(self, action, *args, **kw):
        '''
        This is a specific method that handles sending Login-related and update-related messages to the server.
        '''        
        self.state = ClientState.NONE
        
        logger.debug("Login Write: " + action)
        
        block = QtCore.QByteArray()
        out = QtCore.QDataStream(block, QtCore.QIODevice.ReadWrite)
        out.setVersion(QtCore.QDataStream.Qt_4_2)
        
        out.writeUInt32(0)
        out.writeQString(action)
        for arg in args :
            if type(arg) is IntType:
                out.writeInt(arg)
            elif isinstance(arg, basestring):
                out.writeQString(arg)
            elif type(arg) is FloatType:
                out.writeFloat(arg)
            elif type(arg) is ListType:
                out.writeQVariantList(arg)
            elif type(arg) is DictType:
                out.writeQString(json.dumps(arg))                
            else:
                logger.warn("Uninterpreted Data Type: " + str(type(arg)) + " of value: " + str(arg))
                out.writeQString(str(arg))
        
        out.device().seek(0)
        out.writeUInt32(block.size() - 4)
        self.socket.write(block)   
        QtGui.QApplication.processEvents()

    def writeToServer(self, action, *args, **kw):
        '''
        This method is the workhorse of the client, and is used to send messages, queries and commands to the server.
        '''
        logger.debug("Client: " + action)
        
        block = QtCore.QByteArray()
        out = QtCore.QDataStream(block, QtCore.QIODevice.ReadWrite)
        out.setVersion(QtCore.QDataStream.Qt_4_2)

        out.writeUInt32(0)
        out.writeQString(action)
        out.writeQString(self.login)
        out.writeQString(self.session)        
        
        for arg in args :
            if type(arg) is IntType:
                out.writeInt(arg)
            elif isinstance(arg, basestring):
                out.writeQString(arg)
            elif type(arg) is FloatType:
                out.writeFloat(arg)
            elif type(arg) is ListType:
                out.writeQVariantList(arg)
            elif type(arg) is DictType:
                out.writeQString(json.dumps(arg))                                
            elif type(arg) is QtCore.QFile :       
                arg.open(QtCore.QIODevice.ReadOnly)
                fileDatas = QtCore.QByteArray(arg.readAll())
                #seems that that logger doesn't work
                #logger.debug("file size ", int(fileDatas.size()))
                out.writeInt(fileDatas.size())
                out.writeRawData(fileDatas)

                # This may take a while. We display the progress bar so the user get a feedback
                self.sendFile = True
                self.progress.setLabelText("Sending file to server")
                self.progress.setCancelButton(None)
                self.progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
                self.progress.setAutoClose(True)
                self.progress.setMinimum(0)
                self.progress.setMaximum(100)
                self.progress.setModal(1)
                self.progress.setWindowTitle("Uploading in progress")
 
                self.progress.show()
                arg.close()
            else:
                logger.warn("Uninterpreted Data Type: " + str(type(arg)) + " sent as str: " + str(arg))
                out.writeQString(str(arg))

        out.device().seek(0)        
        out.writeUInt32(block.size() - 4)
        self.bytesToSend = block.size() - 4
    
        self.socket.write(block)
             


    @QtCore.pyqtSlot()
    def readFromServer(self):
        ins = QtCore.QDataStream(self.socket)        
        ins.setVersion(QtCore.QDataStream.Qt_4_2)
        
        while ins.atEnd() == False :
            if self.blockSize == 0:
                if self.socket.bytesAvailable() < 4:
                    return
                self.blockSize = ins.readUInt32()            
            if self.socket.bytesAvailable() < self.blockSize:
                return
            
            action = ins.readQString()
            self.process(action, ins)
            self.blockSize = 0
                                
            
    @QtCore.pyqtSlot()
    def disconnectedFromServer(self):
        logger.warn("Disconnected from lobby server.")

        if self.state == ClientState.ACCEPTED:
            QtGui.QMessageBox.warning(QtGui.QApplication.activeWindow(), "Disconnected from FAF", "The lobby lost the connection to the FAF server.<br/><b>You might still be able to chat.<br/>To play, try reconnecting a little later!</b>", QtGui.QMessageBox.Close)
        
            #Clear the online users lists
            oldplayers = self.players.keys()
            self.players = {}
            self.urls = {}
            self.usersUpdated.emit(oldplayers)
            
            self.disconnected.emit()            
            
            self.mainTabs.setCurrentIndex(0)
            
            for i in range(1, self.mainTabs.count()):
                self.mainTabs.setTabEnabled(i, False)
                self.mainTabs.setTabText(i, "offline")
                
        self.state = ClientState.DROPPED             
            


    @QtCore.pyqtSlot(QtNetwork.QAbstractSocket.SocketError)
    def socketError(self, error):
        logger.error("TCP Socket Error: " + self.socket.errorString())
        if self.state > ClientState.NONE:   # Positive client states deserve user notification.
            QtGui.QMessageBox.critical(None, "TCP Error", "A TCP Connection Error has occurred:<br/><br/><b>" + self.socket.errorString()+"</b>", QtGui.QMessageBox.Close)        


    
    @QtCore.pyqtSlot()
    def forwardLocalBroadcast(self, source, message):
        self.localBroadcast.emit(source, message)
    
    

    #@QtCore.pyqtSlot()
    def forwardPublicBroadcast(self, message):
        self.publicBroadcast.emit(message)
    

    def manage_power(self):
        ''' update the interface accordingly to the power of the user'''
        if self.power >= 1 :
            if self.modMenu == None :
                self.modMenu = self.menuBar().addMenu("Administration")
                
            actionAvatar = QtGui.QAction("Avatar manager", self.modMenu)
            actionAvatar.triggered.connect(self.avatarManager)
            self.modMenu.addAction(actionAvatar)        
    
    def requestAvatars(self, personal):
        if personal :
            self.send(dict(command="avatar", action="list_avatar"))
        else :
            self.send(dict(command="admin", action="requestavatars"))

    def joinChannel(self, user, channel):
        '''Close FA remotly'''
        self.send(dict(command="admin", action="join_channel", users=[user], channel=channel))
   
    def closeFA(self, userToClose):
        '''Close FA remotly'''
        self.send(dict(command="admin", action="closeFA", user=userToClose))

    def closeLobby(self, userToClose):
        '''Close lobby remotly'''
        self.send(dict(command="admin", action="closelobby", user=userToClose))
        
    def addFriend(self, friend):
        '''Adding a new friend by user'''
        self.friends.append(friend)
        self.send(dict(command="social", friends=self.friends)) #LATER: Use this line instead
        #self.writeToServer("ADD_FRIEND", friend)
        self.usersUpdated.emit([friend])

    def addFoe(self, foe):
        '''Adding a new foe by user'''
        self.foes.append(foe)
        self.send(dict(command="social", foes=self.foes)) #LATER: Use this line instead
        #self.writeToServer("ADD_FRIEND", friend)
        self.usersUpdated.emit([foe])

    def remFriend(self, friend):
        '''Removal of a friend by user'''
        self.friends.remove(friend)
        #self.writeToServer("REMOVE_FRIEND", friend)
        self.send(dict(command="social", friends=self.friends)) #LATER: Use this line instead
        self.usersUpdated.emit([friend])

    def remFoe(self, foe):
        '''Removal of a foe by user'''
        self.foes.remove(foe)
        #self.writeToServer("REMOVE_FRIEND", friend)
        self.send(dict(command="social", foes=self.foes)) #LATER: Use this line instead
        self.usersUpdated.emit([foe])

                    
    def process(self, action, stream):
        logger.debug("Server: " + action)

        if action == "PING":
            self.writeToServer("PONG")
    
        elif action == "LOGIN_AVAILABLE" :
            result = stream.readQString()
            name = stream.readQString()
            logger.info("LOGIN_AVAILABLE: " + name + " - " + result)
            self.loginCreation(result)
        
        elif action == 'ACK' :
            bytesWritten = stream.readQString()
            logger.debug("Acknowledged %s bytes" % bytesWritten)
            
            if self.sendFile == True :
                self.progress.setValue(int(bytesWritten)* 100 / self.bytesToSend)
                if int(bytesWritten) >= self.bytesToSend :
                    self.progress.close()
                    self.sendFile = False                    

        elif action == 'ERROR' :
            message = stream.readQString()
            data = stream.readQString()
            logger.error("Protocol Error, server says: " + message + " - " + data)


        elif action == "MESSAGE":
            stream.readQString()
            stream.readQString()
            pass
    
        else:
            try:
                self.dispatch(json.loads(action))
            except:
                logger.error("Error dispatching JSON: " + action, exc_info=sys.exc_info())
                



    # 
    # JSON Protocol v2 Implementation below here
    #
    def send(self, message):
        data = json.dumps(message)
        logger.info("Outgoing JSON Message: " + data)
        self.writeToServer(data)
        
        
    def dispatch(self, message):
        '''
        A fairly pythonic way to process received strings as JSON messages.
        '''
        try:
            if "debug" in message:
                logger.info(message['debug'])

            if "command" in message:                
                cmd = "handle_" + message['command']
                if hasattr(self, cmd):
                    getattr(self, cmd)(message)
                else:                
                    logger.error("Unknown command for JSON." + message['command'])
                    raise "StandardError"
            else:
                logger.debug("No command in message.")                
        except:
            raise #Pass it on to our caller, Malformed Command
      


    def handle_stats(self, message):
        self.statsInfo.emit(message)       

    def handle_welcome(self, message):
        
        if "session" in message :
            self.session = str(message["session"])
        
        if "update" in message : 
            
            # fix a problem with Qt.
            util.settings.beginGroup("window")
            util.settings.remove("geometry")
            util.settings.endGroup()  
            
            if not util.developer():
                logger.warn("Server says that Updating is needed.")
                self.progress.close()
                self.state = ClientState.OUTDATED
                fa.updater.fetchClientUpdate(message["update"])

            else:
                logger.debug("Skipping update because this is a developer version.")
                logger.debug("Login success" )
                self.state = ClientState.ACCEPTED
                
        else :
            logger.debug("Login success" )
            self.state = ClientState.ACCEPTED
            
                
        
    def handle_game_launch(self, message):
        logger.info("Handling game_launch via JSON " + str(message))
        if 'args' in message:            
            arguments = message['args']
        else:
            arguments = []
            
        # Important: This is the race parameter used by ladder search.
        if 'mod' in message:
            modkey = 'mod'
        else:
            modkey = 'featured_mod'
            
        # HACK: Ideally, this comes from the server, too. LATER: search_ranked message
        if message[modkey] == "ladder1v1":
            arguments.append(self.games.race)
            #Player 1v1 rating
            arguments.append('/mean')        
            arguments.append(str(self.players[self.login]["ladder_rating_mean"]))    
            arguments.append('/deviation')        
            arguments.append(str(self.players[self.login]["ladder_rating_deviation"]))            

        else :
            #Player global rating
            arguments.append('/mean')        
            arguments.append(str(self.players[self.login]["rating_mean"]))    
            arguments.append('/deviation')        
            arguments.append(str(self.players[self.login]["rating_deviation"]))            
        
        # Ensure we have the map
        if "mapname" in message:
            fa.exe.checkMap(message['mapname'], True)

        # Writing a file for options
        if "options" in message:
            filename = os.path.join(util.CACHE_DIR, "options.lua")
            options  = QtCore.QFile(filename)
            options.open(QtCore.QIODevice.WriteOnly | QtCore.QIODevice.Text)
            numOpt = 0
            
            options.write("Options = { ")
            
            lenopt = len(message['options'])
            
            for option in message['options'] :
                
                if option == True :
                    options.write("'1'")
                else :
                    options.write("'0'")
                
                numOpt = numOpt + 1
                if lenopt != numOpt :
                    options.write(", ")
                
                
            
            options.write(" }")
            
            options.close()


        #Experimental UPnP Mapper - mappings are removed on app exit
        if self.useUPnP:
            fa.upnp.createPortMapping(self.localIP, self.gamePort, "UDP")
        
        version_info = message.get('version_info', {})
        version_info['lobby'] = util.VERSION_STRING
        
        info = dict(uid = message['uid'], recorder = self.login, featured_mod = message[modkey], game_time=time.time(), version_info=version_info)
        
        
        fa.exe.play(info, self.relayServer.serverPort(), self.gamelogs, arguments)

      

    def handle_tournament_types_info(self, message):
        self.tourneyTypesInfo.emit(message)

    def handle_tournament_info(self, message):
        self.tourneyInfo.emit(message)

    def handle_tutorials_info(self, message):
        self.tutorialsInfo.emit(message)

    def handle_mod_info(self, message):
        self.modInfo.emit(message)    
    
    def handle_game_info(self, message):
        self.gameInfo.emit(message)                    
    
    def handle_replay_vault(self, message):
        self.replayVault.emit(message)
    
    def handle_avatar(self, message):
        if "avatarlist" in message :
            self.avatarList.emit(message["avatarlist"])

    def handle_admin(self, message):
        if "avatarlist" in message :
            self.avatarList.emit(message["avatarlist"])
            
        elif "player_avatar_list" in message :
            print "emitting signal"
            self.playerAvatarList.emit(message)
    
    def handle_social(self, message):
        if "friends" in message:
            self.friends = message["friends"]
            self.usersUpdated.emit(self.players.keys())
        
        if "foes" in message:
            self.foes = message["foes"]
            self.usersUpdated.emit(self.players.keys())
       
        if "autojoin" in message:
            self.autoJoin.emit(message["autojoin"])
        
        if "power" in message:
            self.power = message["power"]
            self.manage_power()

    def handle_player_info(self, message):
        name = message["login"]        
        self.players[name] = message  
        self.usersUpdated.emit([name])
     

    def handle_mod_manager(self, message):
        import functools
        action = message["action"]
        if action == "list" :
            mods = message["mods"]    
            modMenu = self.menuBar().addMenu("Featured Mods Manager")
            for mod in mods :                
                action = QtGui.QAction(mod, modMenu)
                action.triggered.connect(functools.partial(self.featuredMod, mod))
                modMenu.addAction(action)

    def handle_mod_manager_info(self, message):
        self.featuredModManagerInfo.emit(message)
                 
    def avatarManager(self):
        self.requestAvatars(0)
        self.avatarSelection.show()
        
       
                     
    def featuredMod(self, action):
        self.featuredModManager.emit(action)

    def handle_notice(self, message):
        if "text" in message:
            if message["style"] == "error" :
                if self.state != ClientState.NONE :
                    QtGui.QMessageBox.critical(self, "Error from Server", message["text"])
                else :
                    QtGui.QMessageBox.critical(self, "Login Failed", message["text"])
                    self.state = ClientState.REJECTED
    
            elif message["style"] == "warning":
                QtGui.QMessageBox.warning(self, "Warning from Server", message["text"])
            elif message["style"] == "scores":
                self.tray.showMessage("Scores", message["text"], QtGui.QSystemTrayIcon.Information, 3500)
                self.localBroadcast.emit("Scores", message["text"])                                
            else:
                QtGui.QMessageBox.information(self, "Notice from Server", message["text"])
                
        if message["style"] == "kill":
            logger.info("Server has killed your Forged Alliance Process.")
            fa.exe.kill()

        if message["style"] == "kick":
            logger.info("Server has kicked you from the Lobby.")
            self.cleanup()
            
            
