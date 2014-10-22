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
from client.updater import fetchClientUpdate
import fa

'''
Created on Dec 1, 2011

@author: thygrrr
'''

from PyQt4 import QtCore, QtGui, QtNetwork, QtWebKit
from types import IntType, FloatType, ListType, DictType

from client import ClientState, MUMBLE_URL, WEBSITE_URL, WIKI_URL, \
    FORUMS_URL, UNITDB_URL, SUPPORT_URL, TICKET_URL, GAME_PORT_DEFAULT, LOBBY_HOST, \
    LOBBY_PORT, LOCAL_REPLAY_PORT, STEAMLINK_URL

import logging
logger = logging.getLogger(__name__)

HEARTBEAT = 20000

import util
import secondaryServer

import json
import sys
import replays

import time
import os
import random
import notificatation_system as ns

try:
    from profile import playerstats
except:
    pass

class ClientOutdated(StandardError):
    pass


FormClass, BaseClass = util.loadUiType("client/client.ui")


class mousePosition(object):
    def __init__(self, parent):
        self.parent = parent
        self.onLeftEdge = False
        self.onRightEdge = False
        self.onTopEdge = False
        self.onBottomEdge = False
        self.cursorShapeChange = False

    def computeMousePosition(self, pos):
        self.onLeftEdge = pos.x() < 8
        self.onRightEdge = pos.x() > self.parent.size().width() - 8
        self.onTopEdge = pos.y() < 8
        self.onBottomEdge = pos.y() > self.parent.size().height() - 8

        self.onTopLeftEdge = self.onTopEdge and self.onLeftEdge
        self.onBottomLeftEdge = self.onBottomEdge and self.onLeftEdge
        self.onTopRightEdge = self.onTopEdge and self.onRightEdge
        self.onBottomRightEdge = self.onBottomEdge and self.onRightEdge

        self.onEdges = self.onLeftEdge or self.onRightEdge or self.onTopEdge or self.onBottomEdge

    def resetToFalse(self):
        self.onLeftEdge = False
        self.onRightEdge = False
        self.onTopEdge = False
        self.onBottomEdge = False
        self.cursorShapeChange = False

    def isOnEdge(self):
        return self.onEdges

class ClientWindow(FormClass, BaseClass):
    '''
    This is the main lobby client that manages the FAF-related connection and data,
    in particular players, games, ranking, etc.
    Its UI also houses all the other UIs for the sub-modules.
    '''

    topWidget = QtGui.QWidget()


    #These signals are emitted when the client is connected or disconnected from FAF
    connected = QtCore.pyqtSignal()
    disconnected = QtCore.pyqtSignal()

    #This signal is emitted when the client is done rezising
    doneresize = QtCore.pyqtSignal()

    #These signals notify connected modules of game state changes (i.e. reasons why FA is launched)
    viewingReplay = QtCore.pyqtSignal(QtCore.QUrl)

    #Game state controls
    gameEnter = QtCore.pyqtSignal()
    gameExit = QtCore.pyqtSignal()

    #These signals propagate important client state changes to other modules
    statsInfo = QtCore.pyqtSignal(dict)
    tourneyTypesInfo = QtCore.pyqtSignal(dict)
    tutorialsInfo = QtCore.pyqtSignal(dict)
    tourneyInfo = QtCore.pyqtSignal(dict)
    modInfo = QtCore.pyqtSignal(dict)
    gameInfo = QtCore.pyqtSignal(dict)
    modVaultInfo = QtCore.pyqtSignal(dict)
    coopInfo = QtCore.pyqtSignal(dict)
    newGame = QtCore.pyqtSignal(str)
    avatarList = QtCore.pyqtSignal(list)
    playerAvatarList = QtCore.pyqtSignal(dict)
    usersUpdated = QtCore.pyqtSignal(list)
    localBroadcast = QtCore.pyqtSignal(str, str)
    publicBroadcast = QtCore.pyqtSignal(str)
    autoJoin = QtCore.pyqtSignal(list)
    channelsUpdated = QtCore.pyqtSignal(list)
    featuredModManager = QtCore.pyqtSignal(str)
    featuredModManagerInfo = QtCore.pyqtSignal(dict)
    replayVault = QtCore.pyqtSignal(dict)
    coopLeaderBoard = QtCore.pyqtSignal(dict)
    ladderMapsList = QtCore.pyqtSignal(dict)

    #These signals are emitted whenever a certain tab is activated
    showReplays = QtCore.pyqtSignal()
    showMaps = QtCore.pyqtSignal()
    showGames = QtCore.pyqtSignal()
    showTourneys = QtCore.pyqtSignal()
    showLadder = QtCore.pyqtSignal()
    showChat = QtCore.pyqtSignal()
    showGalaxyWar = QtCore.pyqtSignal()
    showMods = QtCore.pyqtSignal()
    showCoop = QtCore.pyqtSignal()

    joinGameFromUser = QtCore.pyqtSignal(str)
    joinReplayFromUser = QtCore.pyqtSignal(str)

    joinGameFromURL = QtCore.pyqtSignal(str)
    joinReplayFromURL = QtCore.pyqtSignal(str)


    # for the auto join ranked
    rankedGameAeon = QtCore.pyqtSignal(bool)
    rankedGameCybran = QtCore.pyqtSignal(bool)
    rankedGameSeraphim = QtCore.pyqtSignal(bool)
    rankedGameUEF = QtCore.pyqtSignal(bool)
    rankedGameRandom = QtCore.pyqtSignal(bool)

    # for team management
    teamInfo = QtCore.pyqtSignal(dict)
    teamInvitation = QtCore.pyqtSignal(dict)

    matchmakerInfo = QtCore.pyqtSignal(dict)

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
        try:
            self.profile = playerstats.Statpage(self)
        except:
            pass

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
        fa.instance.started.connect(self.startedFA)
        fa.instance.finished.connect(self.finishedFA)
        fa.instance.error.connect(self.errorFA)
        self.gameInfo.connect(fa.instance.processGameInfo)

        #Local Replay Server (and relay)
        self.replayServer = fa.replayserver.ReplayServer(self)

        #Local Relay Server
        self.relayServer = fa.relayserver.RelayServer(self)

        #Local proxy servers
        self.proxyServer = fa.proxies.proxies(self)

        #stat server
        self.statsServer = secondaryServer.SecondaryServer("Statistic", 11002, self)

        #create user interface (main window) and load theme
        self.setupUi(self)
        self.setStyleSheet(util.readstylesheet("client/client.css"))

        self.windowsTitleLabel = QtGui.QLabel(self)
        self.windowsTitleLabel.setText("FA Forever " + util.VERSION_STRING)
        self.windowsTitleLabel.setProperty("titleLabel", True)

        self.setWindowTitle("FA Forever " + util.VERSION_STRING)

        # Frameless
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowMinimizeButtonHint)


        self.rubberBand = QtGui.QRubberBand(QtGui.QRubberBand.Rectangle)


        self.mousePosition = mousePosition(self)
        self.installEventFilter(self)

        self.minimize = QtGui.QToolButton(self)
        self.minimize.setIcon(util.icon("client/minimize-button.png"))

        self.maximize = QtGui.QToolButton(self)
        self.maximize.setIcon(util.icon("client/maximize-button.png"))

        close = QtGui.QToolButton(self)
        close.setIcon(util.icon("client/close-button.png"))

        self.minimize.setMinimumHeight(10)
        close.setMinimumHeight(10)
        self.maximize.setMinimumHeight(10)

        close.setIconSize(QtCore.QSize(22, 22))
        self.minimize.setIconSize(QtCore.QSize(22, 22))
        self.maximize.setIconSize(QtCore.QSize(22, 22))

        close.setProperty("windowControlBtn", True)
        self.maximize.setProperty("windowControlBtn", True)
        self.minimize.setProperty("windowControlBtn", True)

        self.menu = self.menuBar()
        self.topLayout.addWidget(self.menu)
        self.topLayout.addWidget(self.windowsTitleLabel)
        self.topLayout.addWidget(self.minimize)
        self.topLayout.addWidget(self.maximize)
        self.topLayout.addWidget(close)
        self.topLayout.insertStretch(1, 500)
        self.topLayout.setSpacing(0)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        self.maxNormal = False

        close.clicked.connect(self.close);
        self.minimize.clicked.connect(self.showSmall)
        self.maximize.clicked.connect(self.showMaxRestore)

        self.moving = False
        self.dragging = False
        self.draggingHover = False
        self.offset = None
        self.curSize = None

        sizeGrip = QtGui.QSizeGrip(self)
        self.mainGridLayout.addWidget(sizeGrip, 2, 2)


        #Wire all important signals
        self.mainTabs.currentChanged.connect(self.mainTabChanged)
        self.topTabs.currentChanged.connect(self.vaultTabChanged)

        #Verrry important step!
        self.loadSettingsPrelogin()

        self.players = {}       # Player names known to the client, contains the player_info messages sent by the server
        self.urls = {}          # user game location URLs - TODO: Should go in self.players

        self.friends = []       # names of the client's friends
        self.foes = []       # names of the client's foes

        self.power = 0          # current user power
        self.email = None
        self.coloredNicknames = False
        #Initialize the Menu Bar according to settings etc.
        self.initMenus()

        #Load the icons for the tabs
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.whatNewTab), util.icon("client/feed.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.chatTab), util.icon("client/chat.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.gamesTab), util.icon("client/games.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.coopTab), util.icon("client/coop.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.vaultsTab), util.icon("client/mods.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.ladderTab), util.icon("client/ladder.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.tourneyTab), util.icon("client/tourney.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.livestreamTab), util.icon("client/twitch.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.replaysTab), util.icon("client/replays.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.tutorialsTab), util.icon("client/tutorials.png"))

        QtWebKit.QWebSettings.globalSettings().setAttribute(QtWebKit.QWebSettings.PluginsEnabled, True)


        #for moderator
        self.modMenu = None

    def eventFilter(self, obj, event):
        if (event.type() == QtCore.QEvent.HoverMove):
            if self.dragging:
                self.draggingHover = True
                self.resizeWidget(self.mapToGlobal(event.pos()))
            else:
                self.draggingHover = False
                if self.maxNormal == False:
                    self.mousePosition.computeMousePosition(event.pos())
                else:
                    self.mousePosition.resetToFalse()
            self.updateCursorShape(event.pos())

        return False


    def updateCursorShape(self, pos):
        if self.mousePosition.onTopLeftEdge or self.mousePosition.onBottomRightEdge:
            self.mousePosition.cursorShapeChange = True
            self.setCursor(QtCore.Qt.SizeFDiagCursor)
        elif self.mousePosition.onTopRightEdge or self.mousePosition.onBottomLeftEdge:
            self.setCursor(QtCore.Qt.SizeBDiagCursor)
            self.mousePosition.cursorShapeChange = True
        elif self.mousePosition.onLeftEdge or self.mousePosition.onRightEdge:
            self.setCursor(QtCore.Qt.SizeHorCursor)
            self.mousePosition.cursorShapeChange = True
        elif self.mousePosition.onTopEdge or self.mousePosition.onBottomEdge:
            self.setCursor(QtCore.Qt.SizeVerCursor)
            self.mousePosition.cursorShapeChange = True
        else:
            if self.mousePosition.cursorShapeChange == True:
                self.unsetCursor()
                self.mousePosition.cursorShapeChange = False

    def showSmall(self):
        self.showMinimized()

    def showMaxRestore(self):
        if(self.maxNormal):
            self.maxNormal = False
            if self.curSize:
                self.setGeometry(self.curSize)

        else:
            self.maxNormal = True
            self.curSize = self.geometry()
            self.setGeometry(QtGui.QDesktopWidget().availableGeometry(self))


    def mouseDoubleClickEvent(self, event):
        self.showMaxRestore()

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.moving = False
        if self.rubberBand.isVisible():
            self.maxNormal = True
            self.curSize = self.geometry()
            self.setGeometry(self.rubberBand.geometry())
            self.rubberBand.hide()
            #self.showMaxRestore()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.mousePosition.isOnEdge() and self.maxNormal == False:
                self.dragging = True
                return
            else :
                self.dragging = False

            self.moving = True
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.dragging and self.draggingHover == False:
            self.resizeWidget(event.globalPos())

        elif self.moving and self.offset != None:
            desktop = QtGui.QDesktopWidget().availableGeometry(self)
            if event.globalPos().y() == 0:
                self.rubberBand.setGeometry(desktop)
                self.rubberBand.show()
            elif event.globalPos().x() == 0:
                desktop.setRight(desktop.right() / 2.0)
                self.rubberBand.setGeometry(desktop)
                self.rubberBand.show()
            elif event.globalPos().x() == desktop.right():
                desktop.setRight(desktop.right() / 2.0)
                desktop.moveLeft(desktop.right())
                self.rubberBand.setGeometry(desktop)
                self.rubberBand.show()

            else:
                self.rubberBand.hide()
                if self.maxNormal == True:
                    self.showMaxRestore()

            self.move(event.globalPos() - self.offset)

    def resizeWidget(self, globalMousePos):
        if globalMousePos.y() == 0:
                self.rubberBand.setGeometry(QtGui.QDesktopWidget().availableGeometry(self))
                self.rubberBand.show()
        else:
                self.rubberBand.hide()


        origRect = self.frameGeometry()

        left, top, right, bottom = origRect.getCoords()
        minWidth = self.minimumWidth()
        minHeight = self.minimumHeight()
        if self.mousePosition.onTopLeftEdge:
            left = globalMousePos.x()
            top = globalMousePos.y()

        elif self.mousePosition.onBottomLeftEdge:
            left = globalMousePos.x();
            bottom = globalMousePos.y();
        elif self.mousePosition.onTopRightEdge:
            right = globalMousePos.x()
            top = globalMousePos.y()
        elif self.mousePosition.onBottomRightEdge:
            right = globalMousePos.x()
            bottom = globalMousePos.y()
        elif self.mousePosition.onLeftEdge:
            left = globalMousePos.x()
        elif self.mousePosition.onRightEdge:
            right = globalMousePos.x()
        elif self.mousePosition.onTopEdge:
            top = globalMousePos.y()
        elif self.mousePosition.onBottomEdge:
            bottom = globalMousePos.y()

        newRect = QtCore.QRect(QtCore.QPoint(left, top), QtCore.QPoint(right, bottom))
        if newRect.isValid():
            if minWidth > newRect.width():
                if left != origRect.left() :
                    newRect.setLeft(origRect.left())
                else:
                    newRect.setRight(origRect.right())
            if minHeight > newRect.height() :
                if top != origRect.top():
                    newRect.setTop(origRect.top())
                else:
                    newRect.setBottom(origRect.bottom())

            self.setGeometry(newRect)


    def setup(self):
        import chat
        import tourneys
        import stats
        import vault
        import games
        import tutorials
        import featuredmods
        import downloadManager
        import modvault
        import coop
        from chat._avatarWidget import avatarWidget

        #download manager
        self.downloader = downloadManager.downloadManager(self)

        # Initialize chat
        self.chat = chat.Lobby(self)

        #build main window with the now active client
        self.ladder = stats.Stats(self)
        self.games = games.Games(self)
        self.tourneys = tourneys.Tourneys(self)
        self.vault = vault.MapVault(self)
        self.modvault = modvault.ModVault(self)
        self.replays = replays.Replays(self)
        self.tutorials = tutorials.Tutorials(self)
        self.Coop = coop.Coop(self)
        self.notificationSystem = ns.NotificationSystem(self)

        # set menu states
        self.actionNsEnabled.setChecked(self.notificationSystem.settings.enabled)

        # Other windows
        self.featuredMods = featuredmods.FeaturedMods(self)
        self.avatarAdmin = self.avatarSelection = avatarWidget(self, None)


        # warning setup
        self.warning = QtGui.QHBoxLayout()

        self.warnPlayer = QtGui.QLabel(self)
        self.warnPlayer.setText("A player of your skill level is currently searching for a 1v1 game. Click a faction to join them! ")
        self.warnPlayer.setAlignment(QtCore.Qt.AlignHCenter)
        self.warnPlayer.setAlignment(QtCore.Qt.AlignVCenter)

        self.warnPlayer.setProperty("warning", True)

        self.rankedAeon = QtGui.QToolButton(self)
        self.rankedCybran = QtGui.QToolButton(self)
        self.rankedSeraphim = QtGui.QToolButton(self)
        self.rankedUEF = QtGui.QToolButton(self)
        self.rankedRandom = QtGui.QToolButton(self)

#        self.rankedAeon.setAutoRaise(0)
#        self.rankedCybran.setAutoRaise(0)
#        self.rankedSeraphim.setAutoRaise(0)
#        self.rankedUEF.setAutoRaise(0)
#        self.rankedRandom.setAutoRaise(0)

        self.rankedAeon.setMaximumSize(25, 25)
        self.rankedCybran.setMaximumSize(25, 25)
        self.rankedSeraphim.setMaximumSize(25, 25)
        self.rankedUEF.setMaximumSize(25, 25)
        self.rankedRandom.setMaximumSize(25, 25)

        self.rankedAeon.setIcon(util.icon("games/automatch/aeon.png"))
        self.rankedCybran.setIcon(util.icon("games/automatch/cybran.png"))
        self.rankedSeraphim.setIcon(util.icon("games/automatch/seraphim.png"))
        self.rankedUEF.setIcon(util.icon("games/automatch/uef.png"))
        self.rankedRandom.setIcon(util.icon("games/automatch/random.png"))


        self.warning.addStretch()
        self.warning.addWidget(self.warnPlayer)
        self.warning.addWidget(self.rankedUEF)
        self.warning.addWidget(self.rankedCybran)
        self.warning.addWidget(self.rankedAeon)
        self.warning.addWidget(self.rankedSeraphim)
        self.warning.addWidget(self.rankedRandom)
        self.warning.addStretch()

        self.mainGridLayout.addLayout(self.warning, 2, 0)


        self.rankedAeon.clicked.connect(self.rankedGameAeon)
        self.rankedCybran.clicked.connect(self.rankedGameCybran)
        self.rankedSeraphim.clicked.connect(self.rankedGameSeraphim)
        self.rankedUEF.clicked.connect(self.rankedGameUEF)
        self.rankedRandom.clicked.connect(self.rankedGameRandom)
        self.warningHide()



    def warningHide(self):
        '''
        hide the warning bar for matchmaker
        '''
        self.warnPlayer.hide()
        self.rankedUEF.hide()
        self.rankedAeon.hide()
        self.rankedCybran.hide()
        self.rankedSeraphim.hide()
        self.rankedRandom.hide()

    def warningShow(self):
        '''
        show the warning bar for matchmaker
        '''
        self.warnPlayer.show()
        self.rankedUEF.show()
        self.rankedAeon.show()
        self.rankedCybran.show()
        self.rankedSeraphim.show()
        self.rankedRandom.show()

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
        self.progress.setLabelText("Closing ForgedAllianceForever.exe")
        if fa.instance.running():
            fa.instance.close()

        #Terminate Lobby Server connection
        if self.socket.state() == QtNetwork.QTcpSocket.ConnectedState:
            self.progress.setLabelText("Closing main connection.")
            self.socket.disconnectFromHost()

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

        if fa.instance.running():
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
        self.actionLink_account_to_Steam.triggered.connect(self.linkToSteam)
        self.actionLinkWebsite.triggered.connect(self.linkWebsite)
        self.actionLinkWiki.triggered.connect(self.linkWiki)
        self.actionLinkForums.triggered.connect(self.linkForums)
        self.actionLinkUnitDB.triggered.connect(self.linkUnitDB)

        self.actionNsSettings.triggered.connect(lambda : self.notificationSystem.on_showSettings())
        self.actionNsEnabled.triggered.connect(lambda enabled : self.notificationSystem.setNotificationEnabled(enabled))

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
        self.actionTeamSetInvitations.triggered.connect(self.updateOptions)
        self.actionSetAutoPostJoin.triggered.connect(self.updateOptions)
        self.actionSetLiveReplays.triggered.connect(self.updateOptions)
        self.actionSaveGamelogs.triggered.connect(self.updateOptions)
        self.actionColoredNicknames.triggered.connect(self.updateOptions)
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
        self.teaminvitations = self.actionTeamSetInvitations.isChecked()
        self.autopostjoin = self.actionSetAutoPostJoin.isChecked()
        self.livereplays = self.actionSetLiveReplays.isChecked()
        self.gamelogs = self.actionSaveGamelogs.isChecked()
        self.coloredNicknames = self.actionColoredNicknames.isChecked()

        self.saveChat()
        self.saveCredentials()
        pass


    @QtCore.pyqtSlot()
    def switchTheme(self):
        util.setTheme(self.sender().theme, True)


    @QtCore.pyqtSlot()
    def switchPath(self):
        fa.wizards.Wizard(self).exec_()

    @QtCore.pyqtSlot()
    def switchPort(self):
        import loginwizards
        loginwizards.gameSettingsWizard(self).exec_()

    @QtCore.pyqtSlot()
    def linkToSteam(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(STEAMLINK_URL))

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
        util.settings.setValue("teaminvitations", self.teaminvitations)
        util.settings.setValue("autopostjoin", self.autopostjoin)
        util.settings.setValue("coloredNicknames", self.coloredNicknames)
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
        util.settings.beginGroup("window")
        geometry = util.settings.value("geometry", None)
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
            self.autopostjoin = (util.settings.value("autopostjoin", "true") == "true")
            self.coloredNicknames = (util.settings.value("coloredNicknames", "false") == "true")
            self.teaminvitations = (util.settings.value("teaminvitations", "false") == "true")

            util.settings.endGroup()
            self.actionColoredNicknames.setChecked(self.coloredNicknames)
            self.actionSetSoundEffects.setChecked(self.soundeffects)
            self.actionSetLiveReplays.setChecked(self.livereplays)
            self.actionSetOpenGames.setChecked(self.opengames)
            self.actionSetJoinsParts.setChecked(self.joinsparts)
            self.actionTeamSetInvitations.setChecked(self.teamInvitations)
            self.actionSetAutoPostJoin.setChecked(self.autopostjoin)
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
        udpSocket = QtNetwork.QUdpSocket(self)
        udpSocket.bind(self.gamePort)
        udpSocket.readyRead.connect(self.processTestGameportDatagram)

        if udpSocket.localPort() != self.gamePort :
            logger.error("The game port set (%i) is not available." % self.gamePort)
            answer = QtGui.QMessageBox.warning(None, "Port Occupied", "FAF has detected that the gameport you choose is not available. Possible reasons:<ul><li><b>FAF is already running</b> (most likely)</li><li>another program is listening on port {port}</li></ul><br>If you click Apply, FAF will port {port2} for this session.".format(port=self.gamePort, port2=udpSocket.localPort()), QtGui.QMessageBox.Apply, QtGui.QMessageBox.Abort)
            if answer == QtGui.QMessageBox.Apply:
                self.gamePort = udpSocket.localPort()

            else :
                udpSocket.close()
                udpSocket.deleteLater()
                return False
        logger.info("The game port is now set to %i" % self.gamePort)
        #now we try sending a packet to the server
        logger.info("sending packet to " + LOBBY_HOST)


        if udpSocket.writeDatagram(self.login, QtNetwork.QHostAddress(QtNetwork.QHostInfo.fromName(LOBBY_HOST).addresses ()[0]), 30351) == -1 :
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

        if not self.udpTest:
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

    def reconnect(self):
        ''' try to reconnect to the server'''
       
        self.socket.disconnected.disconnect(self.disconnectedFromServer)
        self.socket.disconnectFromHost()
        self.socket.disconnected.connect(self.disconnectedFromServer)

        self.progress.setCancelButtonText("Cancel")
        self.progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
        self.progress.setAutoClose(False)
        self.progress.setAutoReset(False)
        self.progress.setModal(1)
        self.progress.setWindowTitle("Re-connecting...")
        self.progress.setLabelText("Re-establishing connection ...")
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
            self.send(dict(command="hello", version=0, login=self.login, password=self.password, unique_id=self.uniqueId, local_ip=self.localIP, session=self.session))
            #self.send(dict(command="ask_session"))    
            return True




    def waitSession(self):
        self.progress.setLabelText("Setting up Session...")
        self.send(dict(command="ask_session"))
        start = time.time()
        while self.session == None and self.progress.isVisible() :
            QtGui.QApplication.processEvents()
            if time.time() - start > 15 :
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
            QtGui.QMessageBox.warning(QtGui.QApplication.activeWindow(), "Unable to login", "It seems that you miss some important DLL.<br>Please install :<br><a href =\"http://www.microsoft.com/download/en/confirmation.aspx?id=8328\">http://www.microsoft.com/download/en/confirmation.aspx?id=8328</a> and <a href = \"http://www.microsoft.com/en-us/download/details.aspx?id=17851\">http://www.microsoft.com/en-us/download/details.aspx?id=17851</a><br><br>You probably have to restart your computer after installing them.<br><br>Please visit this link in case of problems : <a href=\"http://forums.faforever.com/forums/viewforum.php?f=3\">http://forums.faforever.com/forums/viewforum.php?f=3</a>", QtGui.QMessageBox.Close)
            return False
        else :
            self.send(dict(command="hello", version=0, login=self.login, password=self.password, unique_id=self.uniqueId, local_ip=self.localIP))

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

            # live streams
            self.LivestreamWebView.setUrl(QtCore.QUrl("http://www.faforever.com/?page_id=974"))

            util.crash.CRASH_REPORT_USER = self.login

            if not self.testGamePort() :
                return False

            #success: save login data (if requested) and carry on
            self.actionSetAutoLogin.setChecked(self.autologin)
            self.updateOptions()

            self.progress.close()
            #This is a triumph... I'm making a note here: Huge success!
            #logger.debug("Starting heartbeat timer")
            #self.heartbeatTimer.start(HEARTBEAT)
            #self.timeout = 0            
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
    randomcolors = json.loads(util.readfile("client/randomcolors.json"))

    def getUserClan(self, name):
        '''
        Returns a user's clan if any
        '''
        if name in self.players:
            if "clan" in self.players[name]:
                return self.players[name]["clan"]
        return ""

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
            if self.coloredNicknames:
                return self.getRandomColor(name)
            else:
                return self.getColor("player")
        else:
            if self.coloredNicknames:
                return self.getRandomColor(name)
            else:
                return self.getColor("default")


    def getRandomColor(self, name):
        '''Generate a random color from a name'''
        random.seed(name)
        return random.choice(self.randomcolors)

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

            return int(max(0, round((self.players[name]["rating_mean"] - 3 * self.players[name]["rating_deviation"])/100.0)*100))
        else:
            return None



    @QtCore.pyqtSlot()
    def startedFA(self):
        '''
        Slot hooked up to fa.instance when the process has launched.
        It will notify other modules through the signal gameEnter().
        '''
        logger.info("FA has launched in an attached process.")
        self.send(dict(command="fa_state", state="on"))
        self.gameEnter.emit()


    @QtCore.pyqtSlot(int)
    def finishedFA(self, exit_code):
        '''
        Slot hooked up to fa.instance when the process has ended.
        It will notify other modules through the signal gameExit().
        '''
        if not exit_code:
            logger.info("FA has finished with exit code: " + str(exit_code))
        else:
            logger.warn("FA has finished with exit code: " + str(exit_code))
        self.send(dict(command="fa_state", state="off"))
        self.gameExit.emit()

    @QtCore.pyqtSlot(int)
    def errorFA(self, error_code):
        '''
        Slot hooked up to fa.instance when the process has failed to start.
        '''
        if error_code == 0:
            logger.error("FA has failed to start")
            QtGui.QMessageBox.critical(self, "Error from FA", "FA has failed to start.")
        elif error_code == 1:
            logger.error("FA has crashed or killed after starting")
        else:
            text = "FA has failed to start with error code: " + str(error_code)
            logger.error(text)
            QtGui.QMessageBox.critical(self, "Error from FA", text)
        self.send(dict(command="fa_state", state="off"))
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

        if new_tab is self.chatTab:
            self.showChat.emit()

        if new_tab is self.replaysTab:
            self.showReplays.emit()

        if new_tab is self.ladderTab:
            self.showLadder.emit()

        if new_tab is self.tourneyTab:
            self.showTourneys.emit()

        if new_tab is self.coopTab:
            self.showCoop.emit()

    @QtCore.pyqtSlot(int)
    def vaultTabChanged(self, index):
        new_tab = self.topTabs.widget(index)

        if new_tab is self.mapsTab:
            self.showMaps.emit()

        if new_tab is self.modsTab:
            self.showMods.emit()


    def joinGameFromURL(self, url):
        '''
        Tries to join the game at the given URL
        '''
        logger.debug("joinGameFromURL: " + url.toString())
        if fa.instance.available():
            add_mods = []
            try:
                modstr = url.queryItemValue("mods")
                add_mods = json.loads(modstr) # should be a list
            except:
                logger.info("Couldn't load urlquery value 'mods'")
            if fa.check.game(self):
                if fa.check.check(url.queryItemValue("mod"), url.queryItemValue("map"), sim_mods=add_mods):
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


    def serverTimeout(self):
        if self.timeout == 0:
            logger.info("Connection timeout - Checking if server is alive.")
            self.writeToServer("PING")
            self.timeout = self.timeout + 1
        else:
            #self.heartbeatTimer.stop()
            self.socket.abort()
            #logger.info("Connection lost - Trying to reconnect.")
            #if not self.reconnect():
                #logger.error("Unable to reconnect to the server.")
                

    @QtCore.pyqtSlot()
    def readFromServer(self):
        #self.heartbeatTimer.start(HEARTBEAT)
        #self.timeout = 0
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

            # stop hearbeat
            #self.heartbeatTimer.stop()
            #Clear the online users lists
            oldplayers = self.players.keys()
            self.players = {}
            self.urls = {}
            self.usersUpdated.emit(oldplayers)

            self.disconnected.emit()

            self.mainTabs.setCurrentIndex(0)

            for i in range(2, self.mainTabs.count()):
                self.mainTabs.setTabEnabled(i, False)
                self.mainTabs.setTabText(i, "offline")

        self.state = ClientState.DROPPED



    @QtCore.pyqtSlot(QtNetwork.QAbstractSocket.SocketError)
    def socketError(self, error):
        logger.error("TCP Socket Error: " + self.socket.errorString())
        if self.state > ClientState.NONE:   # Positive client states deserve user notification.
            QtGui.QMessageBox.critical(None, "TCP Error", "A TCP Connection Error has occurred:<br/><br/><b>" + self.socket.errorString() + "</b>", QtGui.QMessageBox.Close)
            self.progress.cancel()



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
                self.modMenu = self.menu.addMenu("Administration")

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

    def invite(self, player):
        ''' Send an invitation to be part of my team'''
        self.send(dict(command="social", teaminvite=player))

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
                self.progress.setValue(int(bytesWritten) * 100 / self.bytesToSend)
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
        if message["command"] == "hello" :
            logger.info("Outgoing JSON Message: login.")
        else :
            logger.info("Outgoing JSON Message: " + data)
        self.writeToServer(data)


    def dispatch(self, message):
        '''
        A fairly pythonic way to process received strings as JSON messages.
        '''     

        # add a delay to the notification system
        if 'channels' in message:
            self.notificationSystem.disabledStartup = False
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

        elif "update" in message :

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
                logger.debug("Login success")
                self.state = ClientState.ACCEPTED

        else :
            self.email = message["email"]
            logger.debug("Login success")
            self.state = ClientState.ACCEPTED



    def handle_game_launch(self, message):

        logger.info("Handling game_launch via JSON " + str(message))
        silent = False
        if 'args' in message:
            arguments = message['args']
        else:
            arguments = []



        # Important: This is the race parameter used by ladder search.
        if 'mod' in message:
            modkey = 'mod'  # FIXME: Find out if this is not fully deprecated by now
        else:
            modkey = 'featured_mod'

        # Do some special things depending of the reason of the game launch.
        rank = False

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
            arguments.append('/country ') #Add country command line argument - Vicarian
            country = self.getUserCountry(self.login) #Add country command line argument - Vicarian
            arguments.append(str(country)) #Add country command line argument - Vicarian

        clan = self.getUserClan(self.login)
        if clan:
            arguments.append('/clan')
            arguments.append(clan)

        # Ensure we have the map
        if "mapname" in message:
            fa.check.map(message['mapname'], force=True, silent=silent)

        if "sim_mods" in message:
            fa.mods.checkMods(message['sim_mods'])

        # Writing a file for options
        if "options" in message:
            filename = os.path.join(util.CACHE_DIR, "options.lua")
            options = QtCore.QFile(filename)
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

        game_info = dict(uid=message['uid'], recorder=self.login, featured_mod=message[modkey], game_time=time.time(), version_info=version_info)


        fa.play(game_info, self.relayServer.serverPort(), arguments)



    def handle_coop_info(self, message):
        self.coopInfo.emit(message)

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

    def handle_modvault_list_info(self, message):
        modList = message["modList"]
        for mod in modList:
            self.handle_modvault_info(mod)

    def handle_modvault_info(self, message):
        self.modVaultInfo.emit(message)

    def handle_replay_vault(self, message):
        self.replayVault.emit(message)

    def handle_coop_leaderboard(self, message):
        self.coopLeaderBoard.emit(message)

    def handle_ladder_maps(self, message):
        self.ladderMapsList.emit(message)

    def handle_matchmaker_info(self, message):
        if "action" in message:
            self.matchmakerInfo.emit(message)

        elif "potential" in message:
            if message["potential"] :
                self.warningShow()
            else:
                self.warningHide()

    def handle_avatar(self, message):
        if "avatarlist" in message :
            self.avatarList.emit(message["avatarlist"])

    def handle_admin(self, message):
        if "avatarlist" in message :
            self.avatarList.emit(message["avatarlist"])

        elif "player_avatar_list" in message :
            self.playerAvatarList.emit(message)

    def handle_team_info(self, message):
        self.teamInfo.emit(message)

    def handle_team(self, message):
        self.teamInvitation.emit(message)

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

        if "channels" in message:
            self.channelsUpdated.emit(message["channels"])

    def handle_player_info(self, message):
        name = message["login"]
        self.players[name] = message
        self.usersUpdated.emit([name])


    def handle_mod_manager(self, message):
        import functools
        action = message["action"]
        if action == "list" :
            mods = message["mods"]
            modMenu = self.menu.addMenu("Featured Mods Manager")
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
            fa.instance.kill()

        if message["style"] == "kick":
            logger.info("Server has kicked you from the Lobby.")
            self.cleanup()


