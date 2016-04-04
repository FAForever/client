from functools import partial

from PyQt4.QtCore import QUrl
from PyQt4.QtGui import QLabel, QStyle
from PyQt4.QtNetwork import QAbstractSocket

import config
import connectivity
from base import Client
from config import Settings
import chat
from client.player import Player
from client.players import Players
from client.updater import ClientUpdater
import fa
from connectivity.helper import ConnectivityHelper
from fa import GameSession
from fa.factions import Factions
from fa.game_session import GameSessionState
from ui.status_logo import StatusLogo

'''
Created on Dec 1, 2011

@author: thygrrr
'''

from PyQt4 import QtCore, QtGui, QtNetwork, QtWebKit
from types import IntType, FloatType, ListType, DictType

from client import ClientState, LOBBY_HOST, \
    LOBBY_PORT, LOCAL_REPLAY_PORT

import logging

logger = logging.getLogger(__name__)

import util
import secondaryServer

import json
import sys
import replays

import time
import random
import notifications as ns

FormClass, BaseClass = util.loadUiType("client/client.ui")


class mousePosition(object):
    def __init__(self, parent):
        self.parent = parent
        self.onLeftEdge = False
        self.onRightEdge = False
        self.onTopEdge = False
        self.onBottomEdge = False
        self.cursorShapeChange = False
        self.warning_buttons = dict()
        self.onEdges = False

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

    # These signals are emitted when the client is connected or disconnected from FAF
    connected = QtCore.pyqtSignal()
    authorized = QtCore.pyqtSignal(object)
    disconnected = QtCore.pyqtSignal()

    state_changed = QtCore.pyqtSignal(object)

    # This signal is emitted when the client is done rezising
    doneresize = QtCore.pyqtSignal()

    # These signals notify connected modules of game state changes (i.e. reasons why FA is launched)
    viewingReplay = QtCore.pyqtSignal(QtCore.QUrl)

    # Game state controls
    gameEnter = QtCore.pyqtSignal()
    gameExit = QtCore.pyqtSignal()

    # These signals propagate important client state changes to other modules
    statsInfo = QtCore.pyqtSignal(dict)
    tutorialsInfo = QtCore.pyqtSignal(dict)
    modInfo = QtCore.pyqtSignal(dict)
    gameInfo = QtCore.pyqtSignal(dict)
    modVaultInfo = QtCore.pyqtSignal(dict)
    coopInfo = QtCore.pyqtSignal(dict)
    avatarList = QtCore.pyqtSignal(list)
    playerAvatarList = QtCore.pyqtSignal(dict)
    usersUpdated = QtCore.pyqtSignal(list)
    localBroadcast = QtCore.pyqtSignal(str, str)
    autoJoin = QtCore.pyqtSignal(list)
    channelsUpdated = QtCore.pyqtSignal(list)
    replayVault = QtCore.pyqtSignal(dict)
    coopLeaderBoard = QtCore.pyqtSignal(dict)

    # These signals are emitted whenever a certain tab is activated
    showReplays = QtCore.pyqtSignal()
    showMaps = QtCore.pyqtSignal()
    showGames = QtCore.pyqtSignal()
    showTourneys = QtCore.pyqtSignal()
    showLadder = QtCore.pyqtSignal()
    showChat = QtCore.pyqtSignal()
    showMods = QtCore.pyqtSignal()
    showCoop = QtCore.pyqtSignal()

    matchmakerInfo = QtCore.pyqtSignal(dict)

    remember = Settings.persisted_property('user/remember', type=bool, default_value=True)
    login = Settings.persisted_property('user/login', persist_if=lambda self: self.remember)
    password = Settings.persisted_property('user/password', persist_if=lambda self: self.remember)

    gamelogs = Settings.persisted_property('game/logs', type=bool, default_value=False)
    useUPnP = Settings.persisted_property('game/upnp', type=bool, default_value=True)
    gamePort = Settings.persisted_property('game/port', type=int, default_value=6112)

    def __init__(self, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)

        logger.debug("Client instantiating")

        # Hook to Qt's application management system
        QtGui.QApplication.instance().aboutToQuit.connect(self.cleanup)

        # Init and wire the TCP Network socket to communicate with faforever.com
        self.socket = QtNetwork.QTcpSocket()
        self.socket.readyRead.connect(self.readFromServer)
        self.socket.disconnected.connect(self.disconnectedFromServer)
        self.socket.error.connect(self.socketError)
        self._client_updater = None
        self.blockSize = 0

        self.uniqueId = None

        self.sendFile = False
        self.progress = QtGui.QProgressDialog()
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        self.warning_buttons = {}

        # Tray icon
        self.tray = QtGui.QSystemTrayIcon()
        self.tray.setIcon(util.icon("client/tray_icon.png"))
        self.tray.show()

        self._state = ClientState.NONE
        self.auth_state = ClientState.NONE # Using ClientState for reasons
        self.session = None
        self._connection_attempts = 0

        # Timer for resize events
        self.resizeTimer = QtCore.QTimer(self)
        self.resizeTimer.timeout.connect(self.resized)
        self.preferedSize = 0

        self._receivers = {}

        # Process used to run Forged Alliance (managed in module fa)
        fa.instance.started.connect(self.startedFA)
        fa.instance.finished.connect(self.finishedFA)
        fa.instance.error.connect(self.errorFA)
        self.gameInfo.connect(fa.instance.processGameInfo)

        # Local Replay Server
        self.replayServer = fa.replayserver.ReplayServer(self)

        # GameSession
        self.game_session = None  # type: GameSession

        # ConnectivityTest
        self.connectivity = None  # type: ConnectivityHelper

        self.localIP = None

        # stat server
        self.statsServer = secondaryServer.SecondaryServer("Statistic", 11002, self)

        # create user interface (main window) and load theme
        self.setupUi(self)
        self.setStyleSheet(util.readstylesheet("client/client.css"))
        self.whatNewsView.setHtml("<body style='background-color: #000;'></body>")

        self.setWindowTitle("FA Forever " + util.VERSION_STRING)

        # Frameless
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowMinimizeButtonHint)

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

        self.logo = StatusLogo(self)
        self.logo.disconnect_requested.connect(self.disconnect)
        self.logo.reconnect_requested.connect(self.reconnect)
        self.logo.about_dialog_requested.connect(self.linkAbout)
        self.logo.connectivity_dialog_requested.connect(self.connectivityDialog)

        self.menu = self.menuBar()
        self.topLayout.addWidget(self.logo)
        titleLabel = QLabel("FA Forever" if not config.is_beta() else "FA Forever BETA")
        titleLabel.setProperty('titleLabel', True)
        self.topLayout.addWidget(titleLabel)
        self.topLayout.addStretch(500)
        self.topLayout.addWidget(self.menu)
        self.topLayout.addWidget(self.minimize)
        self.topLayout.addWidget(self.maximize)
        self.topLayout.addWidget(close)
        self.topLayout.setSpacing(0)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        self.maxNormal = False

        close.clicked.connect(self.close)
        self.minimize.clicked.connect(self.showSmall)
        self.maximize.clicked.connect(self.showMaxRestore)

        self.moving = False
        self.dragging = False
        self.draggingHover = False
        self.offset = None
        self.curSize = None

        sizeGrip = QtGui.QSizeGrip(self)
        self.mainGridLayout.addWidget(sizeGrip, 2, 2)

        # Wire all important signals
        self.mainTabs.currentChanged.connect(self.mainTabChanged)
        self.topTabs.currentChanged.connect(self.vaultTabChanged)

        # Handy reference to the Player object representing the logged-in user.
        self.me = None  # FIXME: Move it elsewhere

        self.players = Players(
            self.me)  # Players known to the client, contains the player_info messages sent by the server
        self.urls = {}

        self.power = 0  # current user power
        self.id = 0
        # Initialize the Menu Bar according to settings etc.
        self.initMenus()

        # Load the icons for the tabs
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

        # for moderator
        self.modMenu = None

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value
        self.state_changed.emit(value)

    @QtCore.pyqtSlot(bool)
    def on_actionSavegamelogs_toggled(self, value):
        self.gamelogs = value

    @QtCore.pyqtSlot(bool)
    def on_actionAutoDownloadMods_toggled(self, value):
        Settings.set('mods/autodownload', value is True)

    @QtCore.pyqtSlot(bool)
    def on_actionAutoDownloadMaps_toggled(self, value):
        Settings.set('maps/autodownload', value is True)

    def eventFilter(self, obj, event):
        if (event.type() == QtCore.QEvent.HoverMove):
            self.draggingHover = self.dragging
            if self.dragging:
                self.resizeWidget(self.mapToGlobal(event.pos()))
            else:
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
        if (self.maxNormal):
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
            # self.showMaxRestore()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.mousePosition.isOnEdge() and self.maxNormal == False:
                self.dragging = True
                return
            else:
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
            left = globalMousePos.x()
            bottom = globalMousePos.y()
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
                if left != origRect.left():
                    newRect.setLeft(origRect.left())
                else:
                    newRect.setRight(origRect.right())
            if minHeight > newRect.height():
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
        import downloadManager
        import modvault
        import coop
        from chat._avatarWidget import avatarWidget

        # download manager
        self.downloader = downloadManager.downloadManager(self)

        self.loadSettings()

        # Initialize chat
        self.chat = chat.Lobby(self)
        # Color table used by the following method
        # CAVEAT: This will break if the theme is loaded after the client package is imported
        chat.CHAT_COLORS = json.loads(util.readfile("client/colors.json"))

        # build main window with the now active client
        self.ladder = stats.Stats(self)
        self.games = games.Games(self)
        self.tourneys = tourneys.Tourneys(self)
        self.vault = vault.MapVault(self)
        self.modvault = modvault.ModVault(self)
        self.replays = replays.Replays(self)
        self.tutorials = tutorials.Tutorials(self)
        self.Coop = coop.Coop(self)
        self.notificationSystem = ns.Notifications(self)

        # set menu states
        self.actionNsEnabled.setChecked(self.notificationSystem.settings.enabled)

        # Other windows
        self.avatarAdmin = self.avatarSelection = avatarWidget(self, None)

        # warning setup
        self.warning = QtGui.QHBoxLayout()

        # live streams
        self.LivestreamWebView.setUrl(QtCore.QUrl("http://www.faforever.com/livestream"))

        self.warnPlayer = QtGui.QLabel(self)
        self.warnPlayer.setText(
            "A player of your skill level is currently searching for a 1v1 game. Click a faction to join them! ")
        self.warnPlayer.setAlignment(QtCore.Qt.AlignHCenter)
        self.warnPlayer.setAlignment(QtCore.Qt.AlignVCenter)
        self.warnPlayer.setProperty("warning", True)
        self.warning.addStretch()
        self.warning.addWidget(self.warnPlayer)

        def add_warning_button(faction):
            button = QtGui.QToolButton(self)
            button.setMaximumSize(25, 25)
            button.setIcon(util.icon("games/automatch/%s.png" % faction.to_name()))
            button.clicked.connect(partial(self.games.startSearchRanked, faction))
            self.warning.addWidget(button)
            return button

        self.warning_buttons = {faction: add_warning_button(faction) for faction in Factions}

        self.warning.addStretch()

        self.mainGridLayout.addLayout(self.warning, 2, 0)
        self.warningHide()

    def warningHide(self):
        '''
        hide the warning bar for matchmaker
        '''
        self.warnPlayer.hide()
        for i in self.warning_buttons.values():
            i.hide()

    def warningShow(self):
        '''
        show the warning bar for matchmaker
        '''
        self.warnPlayer.show()
        for i in self.warning_buttons.values():
            i.show()

    def disconnect(self):
        self.state = ClientState.DISCONNECTED
        self.socket.disconnectFromHost()
        self.chat.disconnect()

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

        # Important: If a game is running, offer to terminate it gently
        self.progress.setLabelText("Closing ForgedAllianceForever.exe")
        if fa.instance.running():
            fa.instance.close()

        # Terminate Lobby Server connection
        if self.socket.state() == QtNetwork.QTcpSocket.ConnectedState:
            self.progress.setLabelText("Closing main connection.")
            self.socket.disconnectFromHost()

        # Clear UPnP Mappings...
        if self.useUPnP:
            self.progress.setLabelText("Removing UPnP port mappings")
            fa.upnp.removePortMappings()

        # Terminate local ReplayServer
        if self.replayServer:
            self.progress.setLabelText("Terminating local replay server")
            self.replayServer.close()
            self.replayServer = None

        # Clean up Chat
        if self.chat:
            self.progress.setLabelText("Disconnecting from IRC")
            self.chat.disconnect()
            self.chat = None

        # Get rid of the Tray icon
        if self.tray:
            self.progress.setLabelText("Removing System Tray icon")
            self.tray.deleteLater()
            self.tray = None

        # Terminate UI
        if self.isVisible():
            self.progress.setLabelText("Closing main window")
            self.close()

        self.progress.close()

    def closeEvent(self, event):
        logger.info("Close Event for Application Main Window")
        self.saveWindow()

        if fa.instance.running():
            if QtGui.QMessageBox.question(self, "Are you sure?",
                                          "Seems like you still have Forged Alliance running!<br/><b>Close anyway?</b>",
                                          QtGui.QMessageBox.Yes, QtGui.QMessageBox.No) == QtGui.QMessageBox.No:
                event.ignore()
                return

        return QtGui.QMainWindow.closeEvent(self, event)

    def resizeEvent(self, size):
        self.resizeTimer.start(400)

    def resized(self):
        self.resizeTimer.stop()
        self.doneresize.emit()

    def initMenus(self):
        self.actionLink_account_to_Steam.triggered.connect(partial(self.open_url, Settings.get("STEAMLINK_URL")))
        self.actionLinkWebsite.triggered.connect(partial(self.open_url, Settings.get("WEBSITE_URL")))
        self.actionLinkWiki.triggered.connect(partial(self.open_url, Settings.get("WIKI_URL")))
        self.actionLinkForums.triggered.connect(partial(self.open_url, Settings.get("FORUMS_URL")))
        self.actionLinkUnitDB.triggered.connect(partial(self.open_url, Settings.get("UNITDB_URL")))
        self.actionLinkGitHub.triggered.connect(partial(self.open_url, Settings.get("GITHUB_URL")))

        self.actionNsSettings.triggered.connect(lambda: self.notificationSystem.on_showSettings())
        self.actionNsEnabled.triggered.connect(lambda enabled: self.notificationSystem.setNotificationEnabled(enabled))

        self.actionWiki.triggered.connect(partial(self.open_url, Settings.get("WIKI_URL")))
        self.actionReportBug.triggered.connect(partial(self.open_url, Settings.get("TICKET_URL")))
        self.actionShowLogs.triggered.connect(self.linkShowLogs)
        self.actionTechSupport.triggered.connect(partial(self.open_url, Settings.get("SUPPORT_URL")))
        self.actionAbout.triggered.connect(self.linkAbout)

        self.actionClearCache.triggered.connect(self.clearCache)
        self.actionClearSettings.triggered.connect(self.clearSettings)
        self.actionClearGameFiles.triggered.connect(self.clearGameFiles)

        self.actionSetGamePath.triggered.connect(self.switchPath)
        self.actionSetGamePort.triggered.connect(self.switchPort)

        # Toggle-Options
        self.actionSetAutoLogin.triggered.connect(self.updateOptions)
        self.actionSetAutoLogin.setChecked(self.remember)
        self.actionSetAutoDownloadMods.toggled.connect(self.on_actionAutoDownloadMods_toggled)
        self.actionSetAutoDownloadMods.setChecked(Settings.get('mods/autodownload', type=bool, default=False))
        self.actionSetAutoDownloadMaps.toggled.connect(self.on_actionAutoDownloadMaps_toggled)
        self.actionSetAutoDownloadMaps.setChecked(Settings.get('maps/autodownload', type=bool, default=False))
        self.actionSetSoundEffects.triggered.connect(self.updateOptions)
        self.actionSetOpenGames.triggered.connect(self.updateOptions)
        self.actionSetJoinsParts.triggered.connect(self.updateOptions)
        self.actionSetLiveReplays.triggered.connect(self.updateOptions)
        self.actionSaveGamelogs.toggled.connect(self.on_actionSavegamelogs_toggled)
        self.actionSaveGamelogs.setChecked(self.gamelogs)
        self.actionColoredNicknames.triggered.connect(self.updateOptions)

        # Init themes as actions.
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
        self.menuTheme.addAction("Reload Stylesheet",
                                 lambda: self.setStyleSheet(util.readstylesheet("client/client.css")))

    @QtCore.pyqtSlot()
    def updateOptions(self):
        self.remember = self.actionSetAutoLogin.isChecked()
        self.soundeffects = self.actionSetSoundEffects.isChecked()
        self.opengames = self.actionSetOpenGames.isChecked()
        self.joinsparts = self.actionSetJoinsParts.isChecked()
        self.livereplays = self.actionSetLiveReplays.isChecked()

        self.gamelogs = self.actionSaveGamelogs.isChecked()
        self.players.coloredNicknames = self.actionColoredNicknames.isChecked()

        self.saveChat()

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
    def clearSettings(self):
        result = QtGui.QMessageBox.question(None, "Clear Settings",
                                            "Are you sure you wish to clear all settings, login info, etc. used by this program?",
                                            QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
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

    @QtCore.pyqtSlot(str)
    def open_url(self, url):
        QtGui.QDesktopServices.openUrl(QUrl(url))

    @QtCore.pyqtSlot()
    def linkShowLogs(self):
        util.showInExplorer(util.LOG_DIR)

    @QtCore.pyqtSlot()
    def connectivityDialog(self):
        dialog = connectivity.ConnectivityDialog(self.connectivity)
        dialog.exec_()

    @QtCore.pyqtSlot()
    def linkAbout(self):
        dialog = util.loadUi("client/about.ui")
        dialog.version_label.setText("Version: {}".format(util.VERSION_STRING))
        dialog.exec_()

    def saveWindow(self):
        util.settings.beginGroup("window")
        util.settings.setValue("geometry", self.saveGeometry())
        util.settings.endGroup()

    def saveChat(self):
        util.settings.beginGroup("chat")
        util.settings.setValue("soundeffects", self.soundeffects)
        util.settings.setValue("livereplays", self.livereplays)
        util.settings.setValue("opengames", self.opengames)
        util.settings.setValue("joinsparts", self.joinsparts)
        util.settings.setValue("coloredNicknames", self.players.coloredNicknames)
        util.settings.endGroup()

    def loadSettings(self):
        self.loadChat()
        # Load settings
        util.settings.beginGroup("window")
        geometry = util.settings.value("geometry", None)
        if geometry:
            self.restoreGeometry(geometry)
        util.settings.endGroup()

        util.settings.beginGroup("ForgedAlliance")
        util.settings.endGroup()

    def loadChat(self):
        try:
            util.settings.beginGroup("chat")
            self.soundeffects = (util.settings.value("soundeffects", "true") == "true")
            self.opengames = (util.settings.value("opengames", "true") == "true")
            self.joinsparts = (util.settings.value("joinsparts", "false") == "true")
            self.livereplays = (util.settings.value("livereplays", "true") == "true")
            self.players.coloredNicknames = (util.settings.value("coloredNicknames", "false") == "true")

            util.settings.endGroup()
            self.actionColoredNicknames.setChecked(self.players.coloredNicknames)
            self.actionSetSoundEffects.setChecked(self.soundeffects)
            self.actionSetLiveReplays.setChecked(self.livereplays)
            self.actionSetOpenGames.setChecked(self.opengames)
            self.actionSetJoinsParts.setChecked(self.joinsparts)
        except:
            pass

    def doConnect(self):
        if not self.replayServer.doListen(LOCAL_REPLAY_PORT):
            return False

        # Begin connecting.
        self.socket.connected.connect(self.on_connected)
        self.socket.setSocketOption(QtNetwork.QTcpSocket.KeepAliveOption, 1)
        self.socket.connectToHost(LOBBY_HOST, LOBBY_PORT)
        return True

    def reconnect(self):
        """
        Reconnect to the server
        :return:
        """
        self._connection_attempts += 1
        self.state = ClientState.RECONNECTING
        self.socket.setSocketOption(QtNetwork.QTcpSocket.KeepAliveOption, 1)
        self.socket.connectToHost(LOBBY_HOST, LOBBY_PORT)

    @QtCore.pyqtSlot()
    def on_connected(self):
        self.state = ClientState.ACCEPTED
        self.localIP = self.socket.localAddress()
        self.send(dict(command="ask_session",
                       version=config.VERSION,
                       user_agent="faf-client"))
        self.connected.emit()

    @property
    def can_login(self):
        return self.remember and self.password and self.login

    def show_login_wizard(self):
        from loginwizards import LoginWizard
        wizard = LoginWizard(self)
        wizard.accepted.connect(self.perform_login)
        wizard.exec_()

    def doLogin(self):
        self.state = ClientState.NONE
        if not self.can_login:
            self.show_login_wizard()

    def getColor(self, name):
        return chat.get_color(name)

    @QtCore.pyqtSlot()
    def startedFA(self):
        '''
        Slot hooked up to fa.instance when the process has launched.
        It will notify other modules through the signal gameEnter().
        '''
        logger.info("FA has launched in an attached process.")
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

    @QtCore.pyqtSlot()
    def joinGameFromURL(self, url):
        '''
        Tries to join the game at the given URL
        '''
        logger.debug("joinGameFromURL: " + url.toString())
        if fa.instance.available():
            add_mods = []
            try:
                modstr = url.queryItemValue("mods")
                add_mods = json.loads(modstr)  # should be a list
            except:
                logger.info("Couldn't load urlquery value 'mods'")
            if fa.check.game(self):
                uid, mod, map = url.queryItemValue('uid'), url.queryItemValue('mod'), url.queryItemValue('map')
                if fa.check.check(mod,
                                  map,
                                  sim_mods=add_mods):
                    self.join_game(uid)

    def writeToServer(self, action, *args, **kw):
        '''
        Writes data to the deprecated stream API. Do not use.
        '''
        logger.debug("Client: " + action)

        block = QtCore.QByteArray()
        out = QtCore.QDataStream(block, QtCore.QIODevice.ReadWrite)
        out.setVersion(QtCore.QDataStream.Qt_4_2)

        out.writeUInt32(2 * len(action) + 4)
        out.writeQString(action)

        self.socket.write(block)

    @QtCore.pyqtSlot()
    def readFromServer(self):
        ins = QtCore.QDataStream(self.socket)
        ins.setVersion(QtCore.QDataStream.Qt_4_2)

        while ins.atEnd() == False:
            if self.blockSize == 0:
                if self.socket.bytesAvailable() < 4:
                    return
                self.blockSize = ins.readUInt32()
            if self.socket.bytesAvailable() < self.blockSize:
                return

            action = ins.readQString()
            logger.debug("Server: '%s'" % action)

            if action == "PING":
                self.writeToServer("PONG")
                self.blockSize = 0
                return
            try:
                self.dispatch(json.loads(action))
            except:
                logger.error("Error dispatching JSON: " + action, exc_info=sys.exc_info())

            self.blockSize = 0

    @QtCore.pyqtSlot()
    def disconnectedFromServer(self):
        logger.warn("Disconnected from lobby server.")

        if self.state == ClientState.ACCEPTED:
            # Clear the online users lists
            oldplayers = self.players.keys()
            self.players = Players(self.me)
            self.urls = {}
            self.usersUpdated.emit(oldplayers)

        if self.state != ClientState.DISCONNECTED and self.state != ClientState.SHUTDOWN:
            self.state = ClientState.DROPPED
            if self._connection_attempts < 2:
                logger.info("Reconnecting immediately")
                self.reconnect()
            else:
                timer = QtCore.QTimer(self)
                timer.setSingleShot(True)
                timer.timeout.connect(self.reconnect)
                t = self._connection_attempts * 10000
                timer.start(t)
                logger.info("Scheduling reconnect in {}".format(t / 1000))

        self.disconnected.emit()

    @QtCore.pyqtSlot(QtNetwork.QAbstractSocket.SocketError)
    def socketError(self, error):
        if (error == QAbstractSocket.SocketTimeoutError
                or error == QAbstractSocket.NetworkError
                or error == QAbstractSocket.ConnectionRefusedError
                or error == QAbstractSocket.RemoteHostClosedError):
            logger.info("Timeout/network error: {}".format(self.socket.errorString()))
            self.disconnectedFromServer()
        else:
            self.state = ClientState.DISCONNECTED
            logger.error("Fatal TCP Socket Error: " + self.socket.errorString())

    @QtCore.pyqtSlot()
    def forwardLocalBroadcast(self, source, message):
        self.localBroadcast.emit(source, message)

    def manage_power(self):
        ''' update the interface accordingly to the power of the user'''
        if self.power >= 1:
            if self.modMenu == None:
                self.modMenu = self.menu.addMenu("Administration")

            actionAvatar = QtGui.QAction("Avatar manager", self.modMenu)
            actionAvatar.triggered.connect(self.avatarManager)
            self.modMenu.addAction(actionAvatar)

    def requestAvatars(self, personal):
        if personal:
            self.send(dict(command="avatar", action="list_avatar"))
        else:
            self.send(dict(command="admin", action="requestavatars"))

    def joinChannel(self, username, channel):
        '''Join users to a channel'''
        self.send(dict(command="admin", action="join_channel", user_ids=[self.players[username].id], channel=channel))

    def closeFA(self, username):
        '''Close FA remotly'''
        self.send(dict(command="admin", action="closeFA", user_id=self.players[username].id))

    def closeLobby(self, username):
        '''Close lobby remotly'''
        self.send(dict(command="admin", action="closelobby", user_id=self.players[username].id))

    def addFriend(self, friend_id):
        if friend_id in self.players:
            self.players.friends.add(friend_id)
            self.send(dict(command="social_add", friend=friend_id))
            self.usersUpdated.emit([friend_id])

    def addFoe(self, foe_id):
        if foe_id in self.players:
            self.players.foes.add(foe_id)
            self.send(dict(command="social_add", foe=foe_id))
            self.usersUpdated.emit([foe_id])

    def remFriend(self, friend_id):
        if friend_id in self.players:
            self.players.friends.remove(friend_id)
            self.send(dict(command="social_remove", friend=friend_id))
            self.usersUpdated.emit([friend_id])

    def remFoe(self, foe_id):
        if foe_id in self.players:
            self.players.foes.remove(foe_id)
            self.send(dict(command="social_remove", foe=foe_id))
            self.usersUpdated.emit([foe_id])

    def send(self, message):
        data = json.dumps(message)
        if message.get('command') == 'hello':
            logger.info('Logging in with {}'.format({
                                                        k: v for k, v in message.items() if k != 'password'
                                                        }))
        else:
            logger.info("Outgoing JSON Message: " + data)

        self.writeToServer(data)

    def subscribe_to(self, target, receiver):
        self._receivers[target] = receiver

    def unsubscribe(self, target, receiver):
        del self._receivers[target]

    def dispatch(self, message):
        if "command" in message:
            cmd = "handle_" + message['command']
            if "target" in message:
                receiver = self._receivers.get(message['target'])
                if hasattr(receiver, cmd):
                    getattr(receiver, cmd)(message)
                elif hasattr(receiver, 'handle_message'):
                    receiver.handle_message(message)
                else:
                    logger.warn("No receiver for message {}".format(message))
            else:
                if hasattr(self, cmd):
                    getattr(self, cmd)(message)
                else:
                    logger.error("Unknown JSON command: %s" % message['command'])
                    raise ValueError
        else:
            logger.debug("No command in message.")

    def handle_session(self, message):
        self.session = str(message['session'])
        if self.remember and self.login and self.password:
            self.perform_login()

    @QtCore.pyqtSlot()
    def perform_login(self):
        self.uniqueId = util.uniqueID(self.login, self.session)
        if not self.uniqueId:
            return False
        self.send(dict(command="hello",
                       login=self.login,
                       password=self.password,
                       unique_id=self.uniqueId,
                       session=self.session))
        return True

    def handle_invalid(self, message):
        self.state = ClientState.DISCONNECTED
        raise Exception(message)

    def handle_stats(self, message):
        self.statsInfo.emit(message)

    def handle_update(self, message):
        # Remove geometry settings prior to updating
        # could be incompatible with an updated client.
        Settings.remove('window/geometry')

        logger.warn("Server says we need an update")
        self.progress.close()
        self.state = ClientState.DISCONNECTED
        self._client_updater = ClientUpdater(message['update'])
        self._client_updater.exec_()

    def handle_welcome(self, message):
        self._connection_attempts = 0

        self.id = message["id"]
        self.login = message["login"]
        self.me = Player(id=self.id, login=self.login)
        self.players[self.me.id] = self.me  # FIXME
        self.players.me = self.me  # FIXME
        self.players.login = self.login
        logger.debug("Login success")
        self.state = ClientState.ACCEPTED

        util.crash.CRASH_REPORT_USER = self.login

        if self.useUPnP:
            fa.upnp.createPortMapping(self.socket.localAddress().toString(), self.gamePort, "UDP")

        # update what's new page
        self.whatNewsView.setUrl(QtCore.QUrl(
            "http://www.faforever.com/?page_id=114&username={user}&pwdhash={pwdhash}".format(user=self.login,
                                                                                             pwdhash=self.password)))

        self.updateOptions()

        self.state = ClientState.ONLINE
        self.authorized.emit(self.me)

        # Run an initial connectivity test and initialize a gamesession object
        # when done
        self.connectivity = ConnectivityHelper(self, self.gamePort)
        self.connectivity.connectivity_status_established.connect(self.initialize_game_session)
        self.connectivity.start_test()

    def initialize_game_session(self):
        self.game_session = GameSession(self, self.connectivity)

    def handle_registration_response(self, message):
        if message["result"] == "SUCCESS":
            self.auth_state = ClientState.CREATED
            return

        self.auth_state = ClientState.REJECTED
        self.handle_notice({"style": "notice", "text": message["error"]})

    def search_ranked(self, faction):
        def request_launch():
            msg = {
                'command': 'game_matchmaking',
                'mod': 'ladder1v1',
                'state': 'start',
                'gameport': self.gamePort,
                'faction': faction
            }
            if self.connectivity.state == 'STUN':
                msg['relay_address'] = self.connectivity.relay_address
            self.send(msg)
            self.game_session.ready.disconnect(request_launch)
        if self.game_session:
            self.game_session.ready.connect(request_launch)
            self.game_session.listen()

    def host_game(self, title, mod, visibility, mapname, password):
        def request_launch():
            msg = {
                'command': 'game_host',
                'title': title,
                'mod': mod,
                'visibility': visibility,
                'mapname': mapname,
                'password': password,
            }
            if self.connectivity.state == 'STUN':
                msg['relay_address'] = self.connectivity.relay_address
            self.send(msg)
            self.game_session.ready.disconnect(request_launch)
        if self.game_session:
            self.game_session.ready.connect(request_launch)
            self.game_session.listen()

    def join_game(self, uid, password=None):
        def request_launch():
            msg = {
                'command': 'game_join',
                'uid': uid,
                'gameport': self.gamePort
            }
            if password:
                msg['password'] = password
            if self.connectivity.state == "STUN":
                msg['relay_address'] = self.connectivity.relay_address
            self.send(msg)
            self.game_session.ready.disconnect(request_launch)
        if self.game_session:
            self.game_session.ready.connect(request_launch)
            self.game_session.listen()

    def handle_game_launch(self, message):
        if not self.game_session or not self.connectivity.is_ready:
            logger.error("Not ready for game launch")

        logger.info("Handling game_launch via JSON " + str(message))

        silent = False
        # Do some special things depending of the reason of the game launch.
        rank = False

        # HACK: Ideally, this comes from the server, too. LATER: search_ranked message
        arguments = []
        if message["mod"] == "ladder1v1":
            arguments.append('/' + Factions.to_name(self.games.race))
            # Player 1v1 rating
            arguments.append('/mean')
            arguments.append(str(self.me.ladder_rating_mean))
            arguments.append('/deviation')
            arguments.append(str(self.me.ladder_rating_deviation))
            arguments.append('/players 2')  # Always 2 players in 1v1 ladder
            arguments.append('/team 1')     # Always FFA team

            # Launch the auto lobby
            self.game_session.init_mode = 1

        else:
            # Player global rating
            arguments.append('/mean')
            arguments.append(str(self.me.rating_mean))
            arguments.append('/deviation')
            arguments.append(str(self.me.rating_deviation))
            if self.me.country is not None:
                arguments.append('/country ')
                arguments.append(self.me.country)

            # Launch the normal lobby
            self.game_session.init_mode = 0

        if self.me.clan is not None:
            arguments.append('/clan')
            arguments.append(self.me.clan)

        # Ensure we have the map
        if "mapname" in message:
            fa.check.map(message['mapname'], force=True, silent=silent)

        if "sim_mods" in message:
            fa.mods.checkMods(message['sim_mods'])

        # UPnP Mapper - mappings are removed on app exit
        if self.useUPnP:
            fa.upnp.createPortMapping(self.socket.localAddress().toString(), self.gamePort, "UDP")

        info = dict(uid=message['uid'], recorder=self.login, featured_mod=message['mod'], launched_at=time.time())

        fa.run(info, self.game_session.relay_port, arguments)

    def handle_coop_info(self, message):
        self.coopInfo.emit(message)

    def handle_tutorials_info(self, message):
        self.tutorialsInfo.emit(message)

    def handle_mod_info(self, message):
        self.modInfo.emit(message)

    def handle_game_info(self, message):
        if 'games' in message:
            for game in message['games']:
                self.gameInfo.emit(game)
        else:
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

    def handle_matchmaker_info(self, message):
        if not self.me:
            return
        if "action" in message:
            self.matchmakerInfo.emit(message)
        elif "queues" in message:
            if self.me.ladder_rating_deviation > 200 or self.games.searching:
                return
            key = 'boundary_80s' if self.me.ladder_rating_deviation < 100 else 'boundary_75s'
            show = False
            for q in message['queues']:
                if q['queue_name'] == 'ladder1v1':
                    mu = self.me.ladder_rating_mean
                    for min, max in q[key]:
                        if min < mu < max:
                            show = True
            if show:
                self.warningShow()
            else:
                self.warningHide()

    def handle_avatar(self, message):
        if "avatarlist" in message:
            self.avatarList.emit(message["avatarlist"])

    def handle_admin(self, message):
        if "avatarlist" in message:
            self.avatarList.emit(message["avatarlist"])

        elif "player_avatar_list" in message:
            self.playerAvatarList.emit(message)

    def handle_social(self, message):
        if "friends" in message:
            self.players.friends = set(message["friends"])
            self.usersUpdated.emit(self.players.keys())

        if "foes" in message:
            self.players.foes = set(message["foes"])
            self.usersUpdated.emit(self.players.keys())

        if "channels" in message:
            # Add a delay to the notification system (insane cargo cult)
            self.notificationSystem.disabledStartup = False
            self.channelsUpdated.emit(message["channels"])

        if "autojoin" in message:
            self.autoJoin.emit(message["autojoin"])

        if "power" in message:
            self.power = message["power"]
            self.manage_power()

    def handle_player_info(self, message):
        players = message["players"]

        # Firstly, find yourself. Things get easier once "me" is assigned.
        for player in players:
            if player["id"] == self.id:
                self.me = Player(**player)

        for player in players:
            id = player["id"]
            new_player = Player(**player)

            self.players[id] = new_player
            self.usersUpdated.emit([player['login']])

            if self.me.clan is not None and new_player.clan == self.me.clan:
                self.players.clanlist.add(player['login'])

    def avatarManager(self):
        self.requestAvatars(0)
        self.avatarSelection.show()

    def handle_authentication_failed(self, message):
        QtGui.QMessageBox.warning(self, "Authentication failed", message["text"])
        self.remember = False
        self.state = ClientState.DISCONNECTED
        self.show_login_wizard()

    def handle_notice(self, message):
        if "text" in message:
            style = message.get('style', None)
            if style == "error":
                QtGui.QMessageBox.critical(self, "Error from Server", message["text"])
            elif style == "warning":
                QtGui.QMessageBox.warning(self, "Warning from Server", message["text"])
            elif style == "scores":
                self.tray.showMessage("Scores", message["text"], QtGui.QSystemTrayIcon.Information, 3500)
                self.localBroadcast.emit("Scores", message["text"])
            else:
                QtGui.QMessageBox.information(self, "Notice from Server", message["text"])

        if message["style"] == "kill":
            logger.info("Server has killed your Forged Alliance Process.")
            fa.instance.kill()

        if message["style"] == "kick":
            logger.info("Server has kicked you from the Lobby.")

Client.register(ClientWindow)
