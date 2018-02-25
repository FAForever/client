from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtNetwork import QNetworkAccessManager

import config
from client import ClientState, LOBBY_HOST, LOBBY_PORT
from client.aliasviewer import AliasWindow, AliasSearchWindow
from client.connection import LobbyInfo, ServerConnection, \
        Dispatcher, ConnectionState, ServerReconnecter
from client.gameannouncer import GameAnnouncer
from client.login import LoginWidget
from client.playercolors import PlayerColors
from client.theme_menu import ThemeMenu
from client.user import User, SignallingSet     # TODO - move to util
from downloadManager import PreviewDownloader, AvatarDownloader, \
        MAP_PREVIEW_ROOT
import fa
from fa.factions import Factions
from fa.maps import getUserMapsFolder
from fa.game_runner import GameRunner
from functools import partial
from games.gamemodel import GameModel
from games.gameitem import GameViewBuilder
from games.hostgamewidget import build_launcher
import json
from model.gameset import Gameset, PlayerGameIndex
from model.player import Player
from model.playerset import Playerset
from modvault.utils import MODFOLDER
import notifications as ns
from power import PowerTools
from fa.game_session import GameSession, GameSessionState
from secondaryServer import SecondaryServer
import time
import util
from ui.status_logo import StatusLogo
from ui.busy_widget import BusyWidget
from chat._avatarWidget import AvatarWidget

from model.chat.chat import Chat
from model.chat.channel import ChannelID, ChannelType
from model.chat.chatline import ChatLineMetadataBuilder
from chat.ircconnection import IrcConnection
from chat.chat_view import ChatView
from chat.chat_controller import ChatController
from chat.channel_autojoiner import ChannelAutojoiner
from chat.line_restorer import ChatLineRestorer
from chat.chat_announcer import ChatAnnouncer
from chat.chat_greeter import ChatGreeter
from chat.chatter_model import ChatterLayoutElements
from chat.language_channel_config import LanguageChannelConfig

from client.user import UserRelationModel, UserRelationController, \
        UserRelationTrackers, UserRelations
from updater import ClientUpdateTools

from unitdb import unitdbtab

'''
Created on Dec 1, 2011

@author: thygrrr
'''

from connectivity.ConnectivityDialog import ConnectivityDialog
import logging
logger = logging.getLogger(__name__)

FormClass, BaseClass = util.THEME.loadUiType("client/client.ui")


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


def signal_property(pub):
    priv = "_" + pub
    def get(self):
        return getattr(self, priv)

    def set_(self, v):
        old = getattr(self, priv)
        if v != old:
            setattr(self, priv, v)
            self.updated.emit(pub)

    return property(get, set_)


class ChatConfig(QtCore.QObject):
    updated = QtCore.pyqtSignal(str)

    soundeffects = signal_property("soundeffects")
    joinsparts = signal_property("joinsparts")
    friendsontop = signal_property("friendsontop")
    newbies_channel = signal_property("newbies_channel")
    channel_blink_interval = signal_property("channel_blink_interval")
    channel_ping_timeout = signal_property("channel_ping_timeout")
    max_chat_lines = signal_property("max_chat_lines")
    ignore_foes = signal_property("ignore_foes")

    def __init__(self, settings):
        QtCore.QObject.__init__(self)
        self._settings = settings
        self._soundeffects = None
        self._joinsparts = None
        self._friendsontop = None
        self._newbies_channel = None
        self._channel_blink_interval = None
        self._channel_ping_timeout = None
        self._max_chat_lines = None
        self._ignore_foes = None

        self.hide_chatter_items = SignallingSet()
        self.hide_chatter_items.added.connect(self._emit_hidden_items)
        self.hide_chatter_items.removed.connect(self._emit_hidden_items)

        self.chat_line_trim_count = 1
        self.announcement_channels = []
        self.channel_greeting = []
        self.channels_to_greet_in = []
        self.newbie_channel_game_threshold = 0
        self.load_settings()

    def _emit_hidden_items(self):
        self.updated.emit("hide_chatter_items")

    def load_settings(self):
        s = self._settings
        self.soundeffects = (s.value("chat/soundeffects", "true") == "true")
        self.joinsparts = (s.value("chat/joinsparts", "false") == "true")
        self.friendsontop = (s.value("chat/friendsontop", "false") == "true")
        self.newbies_channel = (s.value("chat/newbiesChannel", "true") ==
                                "true")
        self.ignore_foes = (s.value("chat/ignoreFoes", "true") == "true")

        items = s.value("chat/hide_chatter_items", "")
        items = items.split()
        for item in items:
            try:
                enum_val = ChatterLayoutElements(item)
                self.hide_chatter_items.add(enum_val)
            except ValueError:
                pass

    def save_settings(self):
        s = self._settings
        s.setValue("chat/soundeffects", self.soundeffects)
        s.setValue("chat/joinsparts", self.joinsparts)
        s.setValue("chat/newbiesChannel", self.newbies_channel)
        s.setValue("chat/friendsontop", self.friendsontop)
        s.setValue("chat/ignoreFoes", self.ignore_foes)

        items = " ".join(item.value for item in self.hide_chatter_items)
        s.setValue("chat/hide_chatter_items", items)


class ClientWindow(FormClass, BaseClass):
    """
    This is the main lobby client that manages the FAF-related connection and data,
    in particular players, games, ranking, etc.
    Its UI also houses all the other UIs for the sub-modules.
    """

    state_changed = QtCore.pyqtSignal(object)
    authorized = QtCore.pyqtSignal(object)

    # These signals notify connected modules of game state changes (i.e. reasons why FA is launched)
    viewingReplay = QtCore.pyqtSignal(object)

    # Game state controls
    gameEnter = QtCore.pyqtSignal()
    gameExit = QtCore.pyqtSignal()
    gameFull = QtCore.pyqtSignal()

    # These signals propagate important client state changes to other modules
    localBroadcast = QtCore.pyqtSignal(str, str)
    autoJoin = QtCore.pyqtSignal(list)
    channelsUpdated = QtCore.pyqtSignal(list)

    matchmakerInfo = QtCore.pyqtSignal(dict)

    remember = config.Settings.persisted_property('user/remember', type=bool, default_value=True)
    login = config.Settings.persisted_property('user/login', persist_if=lambda self: self.remember)
    password = config.Settings.persisted_property('user/password', persist_if=lambda self: self.remember)

    gamelogs = config.Settings.persisted_property('game/logs', type=bool, default_value=True)

    use_chat = config.Settings.persisted_property('chat/enabled', type=bool, default_value=True)

    def __init__(self, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)

        logger.debug("Client instantiating")

        # Hook to Qt's application management system
        QtWidgets.QApplication.instance().aboutToQuit.connect(self.cleanup)

        self._nam = QNetworkAccessManager(self)

        self.uniqueId = None

        self.sendFile = False
        self.warning_buttons = {}

        # Tray icon
        self.tray = QtWidgets.QSystemTrayIcon()
        self.tray.setIcon(util.THEME.icon("client/tray_icon.png"))
        self.tray.show()

        self._state = ClientState.NONE
        self.session = None
        self.game_session = None

        # This dictates whether we login automatically in the beginning or
        # after a disconnect. We turn it on if we're sure we have correct
        # credentials and want to use them (if we were remembered or after
        # login) and turn it off if we're getting fresh credentials or
        # encounter a serious server error.
        self._autorelogin = self.remember

        self.lobby_dispatch = Dispatcher()
        self.lobby_connection = ServerConnection(LOBBY_HOST, LOBBY_PORT,
                                                 self.lobby_dispatch.dispatch)
        self.lobby_connection.state_changed.connect(self.on_connection_state_changed)
        self.lobby_reconnecter = ServerReconnecter(self.lobby_connection)

        self.players = Playerset()  # Players known to the client
        self.gameset = Gameset(self.players)
        self._player_game_relation = PlayerGameIndex(self.gameset, self.players)

        fa.instance.gameset = self.gameset  # FIXME (needed fa/game_process L81 for self.game = self.gameset[uid])

        self.lobby_info = LobbyInfo(self.lobby_dispatch, self.gameset, self.players)

        # Handy reference to the User object representing the logged-in user.
        self.me = User(self.players)

        self._chat_model = Chat.build(playerset=self.players,
                                      base_channels=['#aeolus'])

        relation_model = UserRelationModel.build()
        relation_controller = UserRelationController.build(
                relation_model,
                me=self.me,
                settings=config.Settings,
                lobby_info=self.lobby_info,
                lobby_connection=self.lobby_connection
                )
        relation_trackers = UserRelationTrackers.build(
                relation_model,
                playerset=self.players,
                chatterset=self._chat_model.chatters
                )
        self.user_relations = UserRelations(
                relation_model, relation_controller, relation_trackers)
        self.me.relations = self.user_relations

        self.map_downloader = PreviewDownloader(util.MAP_PREVIEW_DIR, MAP_PREVIEW_ROOT)
        self.mod_downloader = PreviewDownloader(util.MOD_PREVIEW_DIR, None)
        self.avatar_downloader = AvatarDownloader()

        # Qt model for displaying active games.
        self.game_model = GameModel(self.me, self.map_downloader, self.gameset)

        self.gameset.added.connect(self.fill_in_session_info)

        self.lobby_info.serverSession.connect(self.handle_session)
        self.lobby_info.serverUpdate.connect(self.handle_update)
        self.lobby_dispatch["registration_response"] = self.handle_registration_response
        self.lobby_dispatch["game_launch"] = self.handle_game_launch
        self.lobby_dispatch["matchmaker_info"] = self.handle_matchmaker_info
        self.lobby_dispatch["player_info"] = self.handle_player_info
        self.lobby_dispatch["notice"] = self.handle_notice
        self.lobby_dispatch["invalid"] = self.handle_invalid
        self.lobby_dispatch["welcome"] = self.handle_welcome
        self.lobby_dispatch["authentication_failed"] = self.handle_authentication_failed

        self.lobby_info.social.connect(self.handle_social)

        # Process used to run Forged Alliance (managed in module fa)
        fa.instance.started.connect(self.startedFA)
        fa.instance.finished.connect(self.finishedFA)
        fa.instance.error.connect(self.errorFA)
        self.gameset.added.connect(fa.instance.newServerGame)

        # Local Replay Server
        self.replayServer = fa.replayserver.ReplayServer(self)

        # ConnectivityTest
        self.connectivity = None  # type: ConnectivityHelper

        # stat server
        self.statsServer = SecondaryServer("Statistic", 11002, self.lobby_dispatch)

        # create user interface (main window) and load theme
        self.setupUi(self)
        util.THEME.stylesheets_reloaded.connect(self.load_stylesheet)
        self.load_stylesheet()

        self.setWindowTitle("FA Forever " + util.VERSION_STRING)

        # Frameless
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.CustomizeWindowHint)

        self.rubberBand = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Rectangle)

        self.mousePosition = mousePosition(self)
        self.installEventFilter(self)

        self.minimize = QtWidgets.QToolButton(self)
        self.minimize.setIcon(util.THEME.icon("client/minimize-button.png"))

        self.maximize = QtWidgets.QToolButton(self)
        self.maximize.setIcon(util.THEME.icon("client/maximize-button.png"))

        close = QtWidgets.QToolButton(self)
        close.setIcon(util.THEME.icon("client/close-button.png"))

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
        titleLabel = QtWidgets.QLabel("FA Forever" if not config.is_beta() else "FA Forever BETA")
        titleLabel.setProperty('titleLabel', True)
        self.topLayout.addWidget(titleLabel)
        self.topLayout.addStretch(500)
        self.topLayout.addWidget(self.menu)
        self.topLayout.addWidget(self.minimize)
        self.topLayout.addWidget(self.maximize)
        self.topLayout.addWidget(close)
        self.topLayout.setSpacing(0)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.maxNormal = False

        close.clicked.connect(self.close)
        self.minimize.clicked.connect(self.showSmall)
        self.maximize.clicked.connect(self.showMaxRestore)

        self.moving = False
        self.dragging = False
        self.draggingHover = False
        self.offset = None
        self.curSize = None

        sizeGrip = QtWidgets.QSizeGrip(self)
        self.mainGridLayout.addWidget(sizeGrip, 2, 2)

        # Wire all important signals
        self._main_tab = -1
        self.mainTabs.currentChanged.connect(self.mainTabChanged)
        self._vault_tab = -1
        self.topTabs.currentChanged.connect(self.vaultTabChanged)

        self.player_colors = PlayerColors(self.me, self.user_relations.model,
                                          util.THEME)

        self.game_announcer = GameAnnouncer(self.gameset, self.me,
                                            self.player_colors)

        self.power = 0  # current user power
        self.id = 0
        # Initialize the Menu Bar according to settings etc.
        self._language_channel_config = LanguageChannelConfig(
            self, config.Settings, util.THEME)
        self.initMenus()

        # Load the icons for the tabs
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.whatNewTab), util.THEME.icon("client/feed.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.chatTab), util.THEME.icon("client/chat.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.gamesTab), util.THEME.icon("client/games.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.coopTab), util.THEME.icon("client/coop.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.vaultsTab), util.THEME.icon("client/mods.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.ladderTab), util.THEME.icon("client/ladder.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.tourneyTab), util.THEME.icon("client/tourney.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.unitdbTab), util.THEME.icon("client/twitch.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.replaysTab), util.THEME.icon("client/replays.png"))
        self.mainTabs.setTabIcon(self.mainTabs.indexOf(self.tutorialsTab), util.THEME.icon("client/tutorials.png"))

        # for moderator
        self.modMenu = None
        self.power_tools = PowerTools.build(
                playerset=self.players,
                lobby_connection=self.lobby_connection,
                theme=util.THEME,
                parent_widget=self,
                settings=config.Settings)

        self._alias_viewer = AliasWindow.build(parent_widget=self)
        self._alias_search_window = AliasSearchWindow(self, self._alias_viewer)
        self._game_runner = GameRunner(self.gameset, self)

        self.connectivity_dialog = None

    def load_stylesheet(self):
        self.setStyleSheet(util.THEME.readstylesheet("client/client.css"))

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value
        self.state_changed.emit(value)

    def on_connection_state_changed(self, state):
        if self.state == ClientState.SHUTDOWN:
            return

        if state == ConnectionState.CONNECTED:
            self.on_connected()
            self.state = ClientState.CONNECTED
        elif state == ConnectionState.DISCONNECTED:
            self.on_disconnected()
            self.state = ClientState.DISCONNECTED
        elif state == ConnectionState.CONNECTING:
            self.state = ClientState.CONNECTING

    def on_connected(self):
        # Enable reconnect in case we used to explicitly stay offline
        self.lobby_reconnecter.enabled = True
        self.lobby_connection.send(dict(command="ask_session",
                                        version=config.VERSION,
                                        user_agent="faf-client"))

    def on_disconnected(self):
        logger.warning("Disconnected from lobby server.")
        self.gameset.clear()
        self.clear_players()

    @QtCore.pyqtSlot(bool)
    def on_actionSavegamelogs_toggled(self, value):
        self.gamelogs = value

    @QtCore.pyqtSlot(bool)
    def on_actionAutoDownloadMods_toggled(self, value):
        config.Settings.set('mods/autodownload', value is True)

    @QtCore.pyqtSlot(bool)
    def on_actionAutoDownloadMaps_toggled(self, value):
        config.Settings.set('maps/autodownload', value is True)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.HoverMove:
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
            self.setGeometry(QtWidgets.QDesktopWidget().availableGeometry(self))

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
            if self.mousePosition.isOnEdge() and not self.maxNormal:
                self.dragging = True
                return
            else:
                self.dragging = False

            self.moving = True
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.dragging and self.draggingHover == False:
            self.resizeWidget(event.globalPos())

        elif self.moving and self.offset is not None:
            desktop = QtWidgets.QDesktopWidget().availableGeometry(self)
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
                if self.maxNormal:
                    self.showMaxRestore()

            self.move(event.globalPos() - self.offset)

    def resizeWidget(self, globalMousePos):
        if globalMousePos.y() == 0:
            self.rubberBand.setGeometry(QtWidgets.QDesktopWidget().availableGeometry(self))
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
        from news import NewsWidget
        from chat import ChatMVC
        from coop import CoopWidget
        from games import GamesWidget
        from tutorials import TutorialsWidget
        from stats import StatsWidget
        from tourneys import TournamentsWidget
        from vault import MapVault
        from modvault import ModVault
        from replays import ReplaysWidget

        self._chat_config = ChatConfig(util.settings)
        self.loadSettings()
        self._chat_config.channel_blink_interval = 500
        self._chat_config.channel_ping_timeout = 60 * 1000
        self._chat_config.max_chat_lines = 200
        self._chat_config.chat_line_trim_count = 50
        self._chat_config.announcement_channels = ['#aeolus']
        self._chat_config.channels_to_greet_in = ['#aeolus']
        self._chat_config.newbie_channel_game_threshold = 50

        wiki_link = util.Settings.get("WIKI_URL")
        wiki_msg = "Check out the wiki: {} for help with common issues.".format(wiki_link)

        self._chat_config.channel_greeting = [
            ("Welcome to Forged Alliance Forever!", "red", "+3"),
            (wiki_msg, "white", "+1"),
            ("", "black", "+1"),
            ("", "black", "+1")]

        self.gameview_builder = GameViewBuilder(self.me,
                                                self.player_colors)
        self.game_launcher = build_launcher(self.players, self.me,
                                            self, self.gameview_builder,
                                            self.map_downloader)
        self._avatar_widget_builder = AvatarWidget.builder(
                parent_widget=self,
                lobby_connection=self.lobby_connection,
                lobby_info=self.lobby_info,
                avatar_dler=self.avatar_downloader,
                theme=util.THEME)

        chat_connection = IrcConnection.build(settings=config.Settings)
        line_metadata_builder = ChatLineMetadataBuilder.build(
            me=self.me,
            user_relations=self.user_relations.model)

        chat_controller = ChatController.build(
                connection=chat_connection,
                model=self._chat_model,
                user_relations=self.user_relations.model,
                chat_config=self._chat_config,
                me=self.me,
                line_metadata_builder=line_metadata_builder)

        target_channel = ChannelID(ChannelType.PUBLIC, '#aeolus')
        chat_view = ChatView.build(
                target_viewed_channel=target_channel,
                model=self._chat_model,
                controller=chat_controller,
                parent_widget=self,
                theme=util.THEME,
                chat_config=self._chat_config,
                player_colors=self.player_colors,
                me=self.me,
                user_relations=self.user_relations,
                power_tools=self.power_tools,
                map_preview_dler=self.map_downloader,
                avatar_dler=self.avatar_downloader,
                avatar_widget_builder=self._avatar_widget_builder,
                alias_viewer=self._alias_viewer,
                client_window=self,
                game_runner=self._game_runner)

        channel_autojoiner = ChannelAutojoiner.build(
                base_channels=['#aeolus'],
                model=self._chat_model,
                controller=chat_controller,
                settings=config.Settings,
                lobby_info=self.lobby_info,
                chat_config=self._chat_config,
                me=self.me)
        chat_greeter = ChatGreeter(
                model=self._chat_model,
                theme=util.THEME,
                chat_config=self._chat_config,
                line_metadata_builder=line_metadata_builder)
        chat_restorer = ChatLineRestorer(self._chat_model)
        chat_announcer = ChatAnnouncer(
            model=self._chat_model,
            chat_config=self._chat_config,
            game_announcer=self.game_announcer,
            line_metadata_builder=line_metadata_builder)

        self._chatMVC = ChatMVC(self._chat_model, line_metadata_builder,
                                chat_connection, chat_controller,
                                channel_autojoiner, chat_greeter,
                                chat_restorer, chat_announcer, chat_view)

        self.authorized.connect(self._connect_chat)

        self.logo = StatusLogo(self, self._chatMVC.model)
        self.logo.disconnect_requested.connect(self.disconnect_)
        self.logo.reconnect_requested.connect(self.reconnect)
        self.logo.chat_reconnect_requested.connect(self.chat_reconnect)
        self.logo.about_dialog_requested.connect(self.linkAbout)
        self.logo.connectivity_dialog_requested.connect(self.connectivityDialog)
        self.topLayout.insertWidget(0, self.logo)

        # build main window with the now active client
        self.news = NewsWidget(self)
        self.coop = CoopWidget(self, self.game_model, self.me,
                               self.gameview_builder, self.game_launcher)
        self.games = GamesWidget(self, self.game_model, self.me,
                                 self.gameview_builder, self.game_launcher)
        self.tutorials = TutorialsWidget(self)
        self.ladder = StatsWidget(self)
        self.tourneys = TournamentsWidget(self)
        self.replays = ReplaysWidget(self, self.lobby_dispatch,
                                     self.gameset, self.players)
        self.mapvault = MapVault(self)
        self.modvault = ModVault(self)
        self.notificationSystem = ns.Notifications(self, self.gameset,
                                                   self.players, self.me)

        self._unitdb = unitdbtab.build_db_tab(
                            config.Settings.get("UNITDB_URL"),
                            config.UNITDB_CONFIG_FILE)

        # TODO: some day when the tabs only do UI we'll have all this in the .ui file
        self.whatNewTab.layout().addWidget(self.news)
        self.chatTab.layout().addWidget(self._chatMVC.view.widget.base)
        self.coopTab.layout().addWidget(self.coop)
        self.gamesTab.layout().addWidget(self.games)
        self.tutorialsTab.layout().addWidget(self.tutorials)
        self.ladderTab.layout().addWidget(self.ladder)
        self.tourneyTab.layout().addWidget(self.tourneys)
        self.replaysTab.layout().addWidget(self.replays)
        self.mapsTab.layout().addWidget(self.mapvault.ui)
        self.unitdbTab.layout().addWidget(self._unitdb.db_widget)
        self.modsTab.layout().addWidget(self.modvault)

        # TODO: hiding some non-functional tabs. Either prune them or implement
        # something useful in them.
        self.mainTabs.removeTab(self.mainTabs.indexOf(self.tutorialsTab))
        self.mainTabs.removeTab(self.mainTabs.indexOf(self.tourneyTab))

        self.mainTabs.setCurrentIndex(self.mainTabs.indexOf(self.whatNewTab))

        # set menu states
        self.actionNsEnabled.setChecked(self.notificationSystem.settings.enabled)

        # warning setup
        self.warning = QtWidgets.QHBoxLayout()

        self.warnPlayer = QtWidgets.QLabel(self)
        self.warnPlayer.setText(
            "A player of your skill level is currently searching for a 1v1 game. Click a faction to join them! ")
        self.warnPlayer.setAlignment(QtCore.Qt.AlignHCenter)
        self.warnPlayer.setAlignment(QtCore.Qt.AlignVCenter)
        self.warnPlayer.setProperty("warning", True)
        self.warning.addStretch()
        self.warning.addWidget(self.warnPlayer)

        def add_warning_button(faction):
            button = QtWidgets.QToolButton(self)
            button.setMaximumSize(25, 25)
            button.setIcon(util.THEME.icon("games/automatch/%s.png" % faction.to_name()))
            button.clicked.connect(partial(self.games.startSearchRanked, faction))
            self.warning.addWidget(button)
            return button

        self.warning_buttons = {faction: add_warning_button(faction) for faction in Factions}

        self.warning.addStretch()

        self.mainGridLayout.addLayout(self.warning, 2, 0)
        self.warningHide()

        self._update_tools = ClientUpdateTools.build(config.VERSION, self,
                                                     self._nam,
                                                     self.lobby_info)
        self._update_tools.mandatory_update_aborted.connect(
            self.close)
        self._update_tools.checker.check()

    def _connect_chat(self, me):
        if not self.use_chat:
            return
        if me.login is None or me.id is None or self.password is None:
            # FIXME: we didn't authorize with the server for some reason.
            # We'll do this check in a more organized fashion in the future.
            return
        self._chatMVC.connection.connect_(me.login, me.id, self.password)

    def warningHide(self):
        """
        hide the warning bar for matchmaker
        """
        self.warnPlayer.hide()
        for i in list(self.warning_buttons.values()):
            i.hide()

    def warningShow(self):
        """
        show the warning bar for matchmaker
        """
        self.warnPlayer.show()
        for i in list(self.warning_buttons.values()):
            i.show()

    def reconnect(self):
        self.lobby_reconnecter.enabled = True
        self.lobby_connection.doConnect()

    def disconnect_(self):
        # Used when the user explicitly demanded to stay offline.
        self.lobby_reconnecter.enabled = False
        self.lobby_connection.disconnect_()
        self._chatMVC.connection.disconnect_()

    def chat_reconnect(self):
        self._connect_chat(self.me)

    @QtCore.pyqtSlot()
    def cleanup(self):
        """
        Perform cleanup before the UI closes
        """
        self.state = ClientState.SHUTDOWN

        progress = QtWidgets.QProgressDialog()
        progress.setMinimum(0)
        progress.setMaximum(0)
        progress.setWindowTitle("FAF is shutting down")
        progress.setMinimum(0)
        progress.setMaximum(0)
        progress.setValue(0)
        progress.setCancelButton(None)
        progress.show()

        # Important: If a game is running, offer to terminate it gently
        progress.setLabelText("Closing ForgedAllianceForever.exe")
        if fa.instance.running():
            fa.instance.close()

        # Terminate Lobby Server connection
        self.lobby_reconnecter.enabled = False
        if self.lobby_connection.socket_connected():
            progress.setLabelText("Closing main connection.")
            self.lobby_connection.disconnect_()

        # Close connectivity dialog
        if self.connectivity_dialog is not None:
            self.connectivity_dialog.close()
            self.connectivity_dialog = None

        # Close game session (and stop faf-ice-adapter.exe)
        if self.game_session is not None:
            self.game_session.closeIceAdapter()
            self.game_session = None

        # Terminate local ReplayServer
        if self.replayServer:
            progress.setLabelText("Terminating local replay server")
            self.replayServer.close()
            self.replayServer = None

        # Clean up Chat
        if self._chatMVC:
            progress.setLabelText("Disconnecting from IRC")
            self._chatMVC.connection.disconnect_()
            self._chatMVC = None

        # Get rid of the Tray icon
        if self.tray:
            progress.setLabelText("Removing System Tray icon")
            self.tray.deleteLater()
            self.tray = None

        # Clear qt message handler to avoid crash at exit
        config.clear_logging_handlers()

        # Terminate UI
        if self.isVisible():
            progress.setLabelText("Closing main window")
            self.close()

        progress.close()

    def closeEvent(self, event):
        logger.info("Close Event for Application Main Window")
        self.saveWindow()

        if fa.instance.running():
            if QtWidgets.QMessageBox.question(self, "Are you sure?", "Seems like you still have Forged Alliance "
                                                                     "running!<br/><b>Close anyway?</b>",
                                              QtWidgets.QMessageBox.Yes,
                                              QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.No:
                event.ignore()
                return

        return QtWidgets.QMainWindow.closeEvent(self, event)

    def initMenus(self):
        self.actionCheck_for_Updates.triggered.connect(self.check_for_updates)
        self.actionUpdate_Settings.triggered.connect(self.show_update_settings)
        self.actionLink_account_to_Steam.triggered.connect(partial(self.open_url, config.Settings.get("STEAMLINK_URL")))
        self.actionLinkWebsite.triggered.connect(partial(self.open_url, config.Settings.get("WEBSITE_URL")))
        self.actionLinkWiki.triggered.connect(partial(self.open_url, config.Settings.get("WIKI_URL")))
        self.actionLinkForums.triggered.connect(partial(self.open_url, config.Settings.get("FORUMS_URL")))
        self.actionLinkUnitDB.triggered.connect(partial(self.open_url, config.Settings.get("UNITDB_URL")))
        self.actionLinkMapPool.triggered.connect(partial(self.open_url, config.Settings.get("MAPPOOL_URL")))
        self.actionLinkGitHub.triggered.connect(partial(self.open_url, config.Settings.get("GITHUB_URL")))

        self.actionNsSettings.triggered.connect(lambda: self.notificationSystem.on_showSettings())
        self.actionNsEnabled.triggered.connect(lambda enabled: self.notificationSystem.setNotificationEnabled(enabled))

        self.actionWiki.triggered.connect(partial(self.open_url, config.Settings.get("WIKI_URL")))
        self.actionReportBug.triggered.connect(partial(self.open_url, config.Settings.get("TICKET_URL")))
        self.actionShowLogs.triggered.connect(self.linkShowLogs)
        self.actionTechSupport.triggered.connect(partial(self.open_url, config.Settings.get("SUPPORT_URL")))
        self.actionAbout.triggered.connect(self.linkAbout)

        self.actionClearCache.triggered.connect(self.clearCache)
        self.actionClearSettings.triggered.connect(self.clearSettings)
        self.actionClearGameFiles.triggered.connect(self.clearGameFiles)

        self.actionSetGamePath.triggered.connect(self.switchPath)

        self.actionShowMapsDir.triggered.connect(lambda: util.showDirInFileBrowser(getUserMapsFolder()))
        self.actionShowModsDir.triggered.connect(lambda: util.showDirInFileBrowser(MODFOLDER))
        self.actionShowReplaysDir.triggered.connect(lambda: util.showDirInFileBrowser(util.REPLAY_DIR))
        self.actionShowThemesDir.triggered.connect(lambda: util.showDirInFileBrowser(util.THEME_DIR))
        # if game.prefs doesn't exist: show_dir -> empty folder / show_file -> 'file doesn't exist' message
        self.actionShowGamePrefs.triggered.connect(lambda: util.showDirInFileBrowser(util.LOCALFOLDER))
        self.actionShowClientConfigFile.triggered.connect(util.showConfigFile)
        #self.actionShowGamePrefs.triggered.connect(lambda: util.showFileInFileBrowser(util.PREFSFILENAME))

        # Toggle-Options
        self.actionSetAutoLogin.triggered.connect(self.updateOptions)
        self.actionSetAutoLogin.setChecked(self.remember)
        self.actionSetAutoDownloadMods.toggled.connect(self.on_actionAutoDownloadMods_toggled)
        self.actionSetAutoDownloadMods.setChecked(config.Settings.get('mods/autodownload', type=bool, default=False))
        self.actionSetAutoDownloadMaps.toggled.connect(self.on_actionAutoDownloadMaps_toggled)
        self.actionSetAutoDownloadMaps.setChecked(config.Settings.get('maps/autodownload', type=bool, default=False))
        self.actionSetSoundEffects.triggered.connect(self.updateOptions)
        self.actionSetOpenGames.triggered.connect(self.updateOptions)
        self.actionSetJoinsParts.triggered.connect(self.updateOptions)
        self.actionSetNewbiesChannel.triggered.connect(self.updateOptions)
        self.actionIgnoreFoes.triggered.connect(self.updateOptions)
        self.actionSetAutoJoinChannels.triggered.connect(self.show_autojoin_settings_dialog)
        self.actionSetLiveReplays.triggered.connect(self.updateOptions)
        self.actionSaveGamelogs.toggled.connect(self.on_actionSavegamelogs_toggled)
        self.actionSaveGamelogs.setChecked(self.gamelogs)
        self.actionColoredNicknames.triggered.connect(self.updateOptions)
        self.actionFriendsOnTop.triggered.connect(self.updateOptions)
        self.actionLanguageChannels.triggered.connect(self._language_channel_config.run)

        self.actionCheckPlayerAliases.triggered.connect(self.checkPlayerAliases)

        self._menuThemeHandler = ThemeMenu(self.menuTheme)
        self._menuThemeHandler.setup(util.THEME.listThemes())
        self._menuThemeHandler.themeSelected.connect(lambda theme: util.THEME.setTheme(theme, True))

        self._chat_vis_actions = {
            ChatterLayoutElements.RANK: self.actionHideChatterRank,
            ChatterLayoutElements.AVATAR: self.actionHideChatterAvatar,
            ChatterLayoutElements.COUNTRY: self.actionHideChatterCountry,
            ChatterLayoutElements.NICK: self.actionHideChatterNick,
            ChatterLayoutElements.STATUS: self.actionHideChatterStatus,
            ChatterLayoutElements.MAP: self.actionHideChatterMap,
        }
        for a in self._chat_vis_actions.values():
            a.triggered.connect(self.updateOptions)

    @QtCore.pyqtSlot()
    def updateOptions(self):
        cc = self._chat_config

        self.remember = self.actionSetAutoLogin.isChecked()
        cc.soundeffects = self.actionSetSoundEffects.isChecked()
        cc.joinsparts = self.actionSetJoinsParts.isChecked()
        cc.newbies_channel = self.actionSetNewbiesChannel.isChecked()
        cc.ignore_foes = self.actionIgnoreFoes.isChecked()
        cc.friendsontop = self.actionFriendsOnTop.isChecked()

        invisible_items = [i for i, a in self._chat_vis_actions.items()
                           if a.isChecked()]
        cc.hide_chatter_items.clear()
        cc.hide_chatter_items |= invisible_items

        self.game_announcer.announce_games = self.actionSetOpenGames.isChecked()
        self.game_announcer.announce_replays = self.actionSetLiveReplays.isChecked()

        self.gamelogs = self.actionSaveGamelogs.isChecked()
        self.player_colors.colored_nicknames = self.actionColoredNicknames.isChecked()

        self.saveChat()


    @QtCore.pyqtSlot()
    def switchPath(self):
        fa.wizards.Wizard(self).exec_()

    @QtCore.pyqtSlot()
    def clearSettings(self):
        result = QtWidgets.QMessageBox.question(None, "Clear Settings", "Are you sure you wish to clear all settings, "
                                                                        "login info, etc. used by this program?",
                                                QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
        if result == QtWidgets.QMessageBox.Yes:
            util.settings.clear()
            util.settings.sync()
            QtWidgets.QMessageBox.information(None, "Restart Needed", "FAF will quit now.")
            QtWidgets.QApplication.quit()

    @QtCore.pyqtSlot()
    def clearGameFiles(self):
        util.clearDirectory(util.BIN_DIR)
        util.clearDirectory(util.GAMEDATA_DIR)

    @QtCore.pyqtSlot()
    def clearCache(self):
        changed = util.clearDirectory(util.CACHE_DIR)
        if changed:
            QtWidgets.QMessageBox.information(None, "Restart Needed", "FAF will quit now.")
            QtWidgets.QApplication.quit()

    # Clear the online users lists
    def clear_players(self):
        self.players.clear()

    @QtCore.pyqtSlot(str)
    def open_url(self, url):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    @QtCore.pyqtSlot()
    def linkShowLogs(self):
        util.showDirInFileBrowser(util.LOG_DIR)

    @QtCore.pyqtSlot()
    def connectivityDialog(self):
        if self.game_session is not None and self.game_session.ice_adapter_client is not None:
            self.connectivity_dialog = ConnectivityDialog(self.game_session.ice_adapter_client)
            self.connectivity_dialog.show()
        else:
            QtWidgets.QMessageBox().information(self, "No game", "The connectivity window is only available during the game.")

    @QtCore.pyqtSlot()
    def linkAbout(self):
        dialog = util.THEME.loadUi("client/about.ui")
        dialog.version_label.setText("Version: {}".format(util.VERSION_STRING))
        dialog.exec_()

    @QtCore.pyqtSlot()
    def check_for_updates(self):
        self._update_tools.checker.check(reset_server=False,
                                         always_notify=True)

    @QtCore.pyqtSlot()
    def show_update_settings(self):
        dialog = self._update_tools.settings_dialog()
        dialog.show()

    def checkPlayerAliases(self):
        self._alias_search_window.run()

    def saveWindow(self):
        util.settings.beginGroup("window")
        util.settings.setValue("geometry", self.saveGeometry())
        util.settings.endGroup()

    def show_autojoin_settings_dialog(self):
        autojoin_channels_list = config.Settings.get('chat/auto_join_channels', [])
        text_of_autojoin_settings_dialog = """
        Enter the list of channels you want to autojoin at startup, separated by ;
        For example: #poker;#newbie
        To disable autojoining channels, leave the box empty and press OK.
        """
        channels_input_of_user, ok = QtWidgets.QInputDialog.getText(self, 'Set autojoin channels',
            text_of_autojoin_settings_dialog, QtWidgets.QLineEdit.Normal, ';'.join(autojoin_channels_list))
        if ok:
            channels = [c.strip() for c in channels_input_of_user.split(';') if c]
            config.Settings.set('chat/auto_join_channels', channels)

    def saveChat(self):
        util.settings.beginGroup("chat")
        util.settings.setValue("livereplays", self.game_announcer.announce_replays)
        util.settings.setValue("opengames", self.game_announcer.announce_games)
        util.settings.setValue("coloredNicknames", self.player_colors.colored_nicknames)
        util.settings.endGroup()
        self._chat_config.save_settings()

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
        cc = self._chat_config
        try:
            util.settings.beginGroup("chat")
            self.game_announcer.announce_games = (util.settings.value("opengames", "true") == "true")
            self.game_announcer.announce_replays = (util.settings.value("livereplays", "true") == "true")
            self.player_colors.colored_nicknames = (util.settings.value("coloredNicknames", "false") == "true")
            util.settings.endGroup()
            cc.load_settings()
            self.actionColoredNicknames.setChecked(self.player_colors.colored_nicknames)
            self.actionFriendsOnTop.setChecked(cc.friendsontop)

            for item in ChatterLayoutElements:
                self._chat_vis_actions[item].setChecked(item in cc.hide_chatter_items)
            self.actionSetSoundEffects.setChecked(cc.soundeffects)
            self.actionSetLiveReplays.setChecked(self.game_announcer.announce_replays)
            self.actionSetOpenGames.setChecked(self.game_announcer.announce_games)
            self.actionSetJoinsParts.setChecked(cc.joinsparts)
            self.actionSetNewbiesChannel.setChecked(cc.newbies_channel)
            self.actionIgnoreFoes.setChecked(cc.ignore_foes)
        except:
            pass

    def doConnect(self):
        if not self.replayServer.doListen():
            return False

        self.lobby_connection.doConnect()
        return True

    def set_remember(self, remember):
        self.remember = remember
        self.actionSetAutoLogin.setChecked(self.remember)  # FIXME - option updating is silly

    def get_creds_and_login(self):
        # Try to autologin, or show login widget if we fail or can't do that.
        if self._autorelogin and self.password and self.login:
            if self.send_login(self.login, self.password):
                return

        self.show_login_widget()

    def show_login_widget(self):
        login_widget = LoginWidget(self.login, self.remember)
        login_widget.finished.connect(self.on_widget_login_data)
        login_widget.rejected.connect(self.on_widget_no_login)
        login_widget.request_quit.connect(self.on_login_widget_quit)
        login_widget.remember.connect(self.set_remember)
        login_widget.exec_()

    def on_widget_login_data(self, login, password):
        self.login = login
        self.password = password

        if self.send_login(login, password):
            return
        self.show_login_widget()

    def on_widget_no_login(self):
        self.disconnect_()

    def on_login_widget_quit(self):
        QtWidgets.QApplication.quit()

    def send_login(self, login, password):
        # Send login data once we have the creds.
        if config.is_beta():  # Replace for develop here to not clobber the real pass
            password = util.password_hash("foo")
        self.uniqueId = util.uniqueID(self.login, self.session)
        if not self.uniqueId:
            QtWidgets.QMessageBox.critical(self,
                                           "Failed to calculate UID",
                                           "Failed to calculate your unique ID"
                                           " (a part of our smurf prevention system).\n"
                                           "Please report this to the tech support forum!")
            return False
        self.lobby_connection.send(dict(command="hello",
                                        login=login,
                                        password=password,
                                        unique_id=self.uniqueId,
                                        session=self.session))
        return True

    @QtCore.pyqtSlot()
    def startedFA(self):
        """
        Slot hooked up to fa.instance when the process has launched.
        It will notify other modules through the signal gameEnter().
        """
        logger.info("FA has launched in an attached process.")
        self.gameEnter.emit()

    @QtCore.pyqtSlot(int)
    def finishedFA(self, exit_code):
        """
        Slot hooked up to fa.instance when the process has ended.
        It will notify other modules through the signal gameExit().
        """
        if not exit_code:
            logger.info("FA has finished with exit code: " + str(exit_code))
        else:
            logger.warning("FA has finished with exit code: " + str(exit_code))
        self.gameExit.emit()

    @QtCore.pyqtSlot(QtCore.QProcess.ProcessError)
    def errorFA(self, error_code):
        """
        Slot hooked up to fa.instance when the process has failed to start.
        """
        logger.error("FA has died with error: " + fa.instance.errorString())
        if error_code == 0:
            logger.error("FA has failed to start")
            QtWidgets.QMessageBox.critical(self, "Error from FA", "FA has failed to start.")
        elif error_code == 1:
            logger.error("FA has crashed or killed after starting")
        else:
            text = "FA has failed to start with error code: " + str(error_code)
            logger.error(text)
            QtWidgets.QMessageBox.critical(self, "Error from FA", text)
        self.gameExit.emit()

    def _tabChanged(self, tab, curr, prev):
        """
        The main visible tab (module) of the client's UI has changed.
        In this case, other modules may want to load some data or cease
        particularly CPU-intensive interactive functionality.
        """
        new_tab = tab.widget(curr)
        old_tab = tab.widget(prev)

        if old_tab is not None:
            tab = old_tab.layout().itemAt(0).widget()
            if isinstance(tab, BusyWidget):
                tab.busy_left()
        if new_tab is not None:
            tab = new_tab.layout().itemAt(0).widget()
            if isinstance(tab, BusyWidget):
                tab.busy_entered()
        # FIXME - special concession for chat tab. In the future we should
        # separate widgets from controlling classes, just like chat tab does -
        # then we'll refactor this part.
        if new_tab is self.chatTab:
            self._chatMVC.view.entered()


    @QtCore.pyqtSlot(int)
    def mainTabChanged(self, curr):
        self._tabChanged(self.mainTabs, curr, self._main_tab)
        self._main_tab = curr

    @QtCore.pyqtSlot(int)
    def vaultTabChanged(self, curr):
        self._tabChanged(self.topTabs, curr, self._vault_tab)
        self._vault_tab = curr

    @QtCore.pyqtSlot()
    def joinGameFromURL(self, gurl):
        """
        Tries to join the game at the given URL
        """
        logger.debug("joinGameFromURL: " + gurl.to_url().toString())
        if fa.instance.available():
            add_mods = []
            try:
                add_mods = json.loads(gurl.mods)  # should be a list
            except json.JSONDecodeError:
                logger.info("Couldn't load urlquery value 'mods'")
            if fa.check.game(self):
                if fa.check.check(gurl.mod, gurl.map, sim_mods=add_mods):
                    self.join_game(gurl.uid)

    def view_replays(self, name):
        self.replays.set_player(name)
        self.mainTabs.setCurrentIndex(self.mainTabs.indexOf(self.replaysTab))

    def view_in_leaderboards(self, user):
        self.ladder.set_player(user)
        self.mainTabs.setCurrentIndex(self.mainTabs.indexOf(self.ladderTab))

    @QtCore.pyqtSlot()
    def forwardLocalBroadcast(self, source, message):
        self.localBroadcast.emit(source, message)

    def manage_power(self):
        """ update the interface accordingly to the power of the user """
        if self.power_tools.power >= 1:
            if self.modMenu is None:
                self.modMenu = self.menu.addMenu("Administration")

            actionLobbyKick = QtWidgets.QAction("Close player's FAF Client...", self.modMenu)
            actionLobbyKick.triggered.connect(self._on_lobby_kick_triggered)
            self.modMenu.addAction(actionLobbyKick)

            actionCloseFA = QtWidgets.QAction("Close Player's Game...", self.modMenu)
            actionCloseFA.triggered.connect(self._close_game_dialog)
            self.modMenu.addAction(actionCloseFA)

    def _close_game_dialog(self):
        self.power_tools.view.close_game_dialog.show()

    # Needed so that we ignore the bool from the triggered() signal
    def _on_lobby_kick_triggered(self):
        self.power_tools.view.kick_dialog()

    def joinChannel(self, username, channel):
        """ Join users to a channel """
        self.lobby_connection.send(dict(command="admin", action="join_channel",
                                        user_ids=[self.players.getID(username)], channel=channel))

    def closeFA(self, username):
        self.power_tools.actions.close_fa(username)

    def closeLobby(self, username=""):
        self.power_tools.actions.kick_player(username)

    def handle_session(self, message):
        self.session = str(message['session'])
        self.get_creds_and_login()

    def handle_update(self, message):
        # Remove geometry settings prior to updating
        # could be incompatible with an updated client.
        config.Settings.remove('window/geometry')
        logger.warning("Server says we need an update")

    def handle_welcome(self, message):
        self.state = ClientState.LOGGED_IN
        self._autorelogin = True
        self.id = message["id"]
        self.login = message["login"]

        self.me.onLogin(message["login"], message["id"])
        logger.debug("Login success")

        util.crash.CRASH_REPORT_USER = self.login


        self.updateOptions()

        self.authorized.emit(self.me)

        if self.game_session is None:
            self.game_session = GameSession(player_id=message["id"], player_login=message["login"])
        elif self.game_session.game_uid != None:
            self.lobby_connection.send({'command': 'restore_game_session',
                                        'game_id': self.game_session.game_uid})


        self.game_session.gameFullSignal.connect(self.game_full)

    def handle_registration_response(self, message):
        if message["result"] == "SUCCESS":
            return

        self.handle_notice({"style": "notice", "text": message["error"]})

    def search_ranked(self, faction):
        msg = {
            'command': 'game_matchmaking',
            'mod': 'ladder1v1',
            'state': 'start',
            'gameport': 0,
            'faction': faction
        }
        self.lobby_connection.send(msg)

    def host_game(self, title, mod, visibility, mapname, password, is_rehost=False):
        msg = {
            'command': 'game_host',
            'title': title,
            'mod': mod,
            'visibility': visibility,
            'mapname': mapname,
            'password': password,
            'is_rehost': is_rehost
        }
        self.lobby_connection.send(msg)

    def join_game(self, uid, password=None):
        msg = {
            'command': 'game_join',
            'uid': uid,
            'gameport': 0
        }
        if password:
            msg['password'] = password
        self.lobby_connection.send(msg)

    def handle_game_launch(self, message):

        self.game_session.startIceAdapter()

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
            arguments.append(str(self.me.player.ladder_rating_mean))
            arguments.append('/deviation')
            arguments.append(str(self.me.player.ladder_rating_deviation))
            arguments.append('/players 2')  # Always 2 players in 1v1 ladder
            arguments.append('/team 1')     # Always FFA team

            # Launch the auto lobby
            self.game_session.setLobbyInitMode("auto")
        else:
            # Player global rating
            arguments.append('/mean')
            arguments.append(str(self.me.player.rating_mean))
            arguments.append('/deviation')
            arguments.append(str(self.me.player.rating_deviation))
            if self.me.player.country is not None:
                arguments.append('/country ')
                arguments.append(self.me.player.country)

            # Launch the normal lobby
            self.game_session.setLobbyInitMode("normal")

        if self.me.player.clan is not None:
            arguments.append('/clan')
            arguments.append(self.me.player.clan)

        # Ensure we have the map
        if "mapname" in message:
            fa.check.map_(message['mapname'], force=True, silent=silent)

        if "sim_mods" in message:
            fa.mods.checkMods(message['sim_mods'])

        info = dict(uid=message['uid'], recorder=self.login, featured_mod=message['mod'], launched_at=time.time())

        self.game_session.game_uid = message['uid']

        fa.run(info, self.game_session.relay_port, self.replayServer.serverPort(), arguments, self.game_session.game_uid)

    def fill_in_session_info(self, game):
        # sometimes we get the game_info message before a game session was created
        if self.game_session and game.uid == self.game_session.game_uid:
            self.game_session.game_map = game.mapname
            self.game_session.game_mod = game.featured_mod
            self.game_session.game_name = game.title
            self.game_session.game_visibility = game.visibility.value

    def handle_matchmaker_info(self, message):
        if not self.me.player:
            return
        if "action" in message:
            self.matchmakerInfo.emit(message)
        elif "queues" in message:
            if self.me.player.ladder_rating_deviation > 200 or self.games.searching:
                return
            key = 'boundary_80s' if self.me.player.ladder_rating_deviation < 100 else 'boundary_75s'
            show = False
            for q in message['queues']:
                if q['queue_name'] == 'ladder1v1':
                    mu = self.me.player.ladder_rating_mean
                    for min, max in q[key]:
                        if min < mu < max:
                            show = True
            if show:
                self.warningShow()
            else:
                self.warningHide()

    def handle_social(self, message):
        if "channels" in message:
            # Add a delay to the notification system (insane cargo cult)
            self.notificationSystem.disabledStartup = False
            self.channelsUpdated.emit(message["channels"])

        if "power" in message:
            self.power_tools.power = message["power"]
            self.manage_power()

    def handle_player_info(self, message):
        players = message["players"]

        # Fix id being a Python keyword
        for player in players:
            player["id_"] = player["id"]
            del player["id"]

        for player in players:
            id_ = int(player["id_"])
            logger.debug('Received update about player {}'.format(id_))
            if id_ in self.players:
                self.players[id_].update(**player)
            else:
                self.players[id_] = Player(**player)

    def handle_authentication_failed(self, message):
        QtWidgets.QMessageBox.warning(self, "Authentication failed", message["text"])
        self._autorelogin = False
        self.get_creds_and_login()

    def handle_notice(self, message):
        if "text" in message:
            style = message.get('style', None)
            if style == "error":
                QtWidgets.QMessageBox.critical(self, "Error from Server", message["text"])
            elif style == "warning":
                QtWidgets.QMessageBox.warning(self, "Warning from Server", message["text"])
            elif style == "scores":
                self.tray.showMessage("Scores", message["text"], QtWidgets.QSystemTrayIcon.Information, 3500)
                self.localBroadcast.emit("Scores", message["text"])
            else:
                QtWidgets.QMessageBox.information(self, "Notice from Server", message["text"])

        if message["style"] == "kill":
            logger.info("Server has killed your Forged Alliance Process.")
            fa.instance.kill()

        if message["style"] == "kick":
            logger.info("Server has kicked you from the Lobby.")

        # This is part of the protocol - in this case we should not relogin automatically.
        if message["style"] in ["error", "kick"]:
            self._autorelogin = False

    def handle_invalid(self, message):
        # We did something wrong and the server will disconnect, let's not
        # reconnect and potentially cause the same error again and again
        self.lobby_reconnecter.enabled = False
        raise Exception(message)

    def game_full(self):
        self.gameFull.emit()
