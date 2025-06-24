import json
import logging
import os
import time

from pydantic import ValidationError
from PyQt6 import QtCore
from PyQt6 import QtGui
from PyQt6 import QtWidgets
from PyQt6.QtNetwork import QNetworkAccessManager
from PyQt6.QtNetwork import QNetworkReply
from PyQt6.QtNetwork import QNetworkRequest
from PyQt6.QtWidgets import QTreeWidget
from PyQt6.QtWidgets import QTreeWidgetItem

from src import client
from src import fa
from src import util
from src.api.models.Leaderboard import Leaderboard
from src.api.replaysapi import ReplaysApiConnector
from src.api.stats_api import LeaderboardApiConnector
from src.config import Settings
from src.downloadManager import DownloadRequest
from src.fa.replay import replay
from src.model.game import GameState
from src.replays.models import MetadataModel
from src.replays.replaydetails.replaycard import ReplayDetailsCard
from src.replays.replayitem import ReplayItem
from src.replays.replayitem import ReplayItemDelegate
from src.replays.replayToolbox import ReplayToolboxHandler
from src.util.gameurl import GameUrl
from src.util.gameurl import GameUrlType

logger = logging.getLogger(__name__)

# Replays uses the new Inheritance Based UI creation pattern
# This allows us to do all sorts of awesome stuff by overriding methods etc.

FormClass, BaseClass = util.THEME.loadUiType("replays/replays.ui")


class LiveReplayItem(QtWidgets.QTreeWidgetItem):
    LIVEREPLAY_DELAY = 5 * 60

    def __init__(self, game):
        QtWidgets.QTreeWidgetItem.__init__(self)
        self._game = game
        if game.launched_at is not None:
            self.launch_time = game.launched_at
        else:
            self.launch_time = time.time()
        self._map_dl_request = DownloadRequest()
        self._map_dl_request.done.connect(self._map_preview_downloaded)

        self._game.updated.connect(self._update_game)
        self._set_show_delay()
        self._update_game(self._game)

    def _set_show_delay(self):
        if time.time() - self.launch_time < self.LIVEREPLAY_DELAY:
            self.setHidden(True)
            # Wait until the replayserver makes the replay available
            elapsed_time = time.time() - self.launch_time
            delay_time = self.LIVEREPLAY_DELAY - elapsed_time
            QtCore.QTimer.singleShot(int(1000 * delay_time), self._show_item)

    def _show_item(self):
        self.setHidden(False)

    def _map_preview_downloaded(self, preview_file: str, pixmap: QtGui.QPixmap) -> None:
        if util.pretty_decoded_basename(preview_file) != self._game.mapname:
            return
        self.setIcon(0, QtGui.QIcon(pixmap))

    def _update_game(self, game):
        if game.state == GameState.CLOSED:
            return

        self.takeChildren()     # Clear the children of this item
        self._set_debug_tooltip(game)
        self._set_game_map_icon(game)
        self._set_misc_formatting(game)
        self._set_color(game)
        self._generate_player_subitems(game)

    def _set_debug_tooltip(self, game):
        info = game.to_dict()
        tip = ""
        for key in list(info.keys()):
            tip += f"'{key}' : '{info[key]}'<br/>"
        self.setToolTip(1, tip)

    def _set_game_map_icon(self, game):
        if game.featured_mod == "coop":  # no map icons for coop
            icon = util.THEME.icon("games/unknown_map.png")
        else:
            icon = fa.maps.preview(game.mapname)
            if not icon:
                dler = client.instance.map_preview_downloader
                dler.download_preview(game.mapname, self._map_dl_request)
                icon = util.THEME.icon("games/unknown_map.png")
        self.setIcon(0, icon)

    def _set_misc_formatting(self, game):
        self.setToolTip(0, fa.maps.getDisplayName(game.mapname))

        time_fmt = "%Y-%m-%d  -  %H:%M"
        launch_time = time.strftime(time_fmt, time.localtime(self.launch_time))
        self.setText(0, launch_time)

        colors = client.instance.player_colors
        self.setForeground(0, QtGui.QColor(colors.get_color("default")))
        if game.featured_mod == "ladder1v1":
            self.setText(1, game.title)
        else:
            self.setText(1, game.title + "    -    [host: " + game.host + "]")
        self.setForeground(1, QtGui.QColor(colors.get_color("player")))
        self.setText(2, game.featured_mod)
        self.setTextAlignment(2, QtCore.Qt.AlignmentFlag.AlignCenter)

    def _is_me(self, name):
        return client.instance.login == name

    def _is_friend(self, name: str) -> bool:
        playerid = client.instance.players.getID(name)
        return client.instance.user_relations.model.is_friend(playerid)

    def _is_online(self, name):
        return name in client.instance.players

    def _set_color(self, game):
        my_game = any(self._is_me(p) for p in game.players)
        friend_game = any(self._is_friend(p) for p in game.players)
        if my_game:
            my_color = "self"
        elif friend_game:
            my_color = "friend"
        else:
            my_color = "player"
        colors = client.instance.player_colors
        self.setForeground(1, QtGui.QColor(colors.get_color(my_color)))

    def _generate_player_subitems(self, game):
        if not game.teams:
            self.setDisabled(True)
            return
        for player in game.playing_players:  # observers don't stream replays
            playeritem = self._create_playeritem(game, player)
            self.addChild(playeritem)

    def _create_playeritem(self, game, name):
        item = QtWidgets.QTreeWidgetItem()
        item.setText(0, name)

        if self._is_me(name):
            player_color = "self"
        elif self._is_friend(name):
            player_color = "friend"
        elif self._is_online(name):
            player_color = "player"
        else:
            player_color = "default"
        colors = client.instance.player_colors
        item.setForeground(0, QtGui.QColor(colors.get_color(player_color)))

        if self._is_online(name):
            item.gurl = self._generate_livereplay_link(game, name)
            item.setToolTip(0, item.gurl.to_url().toString())
            item.setIcon(0, util.THEME.icon("replays/replay.png"))
        else:
            item.setDisabled(True)
        return item

    def _generate_livereplay_link(self, game, name):
        return GameUrl(
            GameUrlType.LIVE_REPLAY, game.mapname,
            game.featured_mod, game.uid, name,
        )

    def __lt__(self, other):
        return self.launch_time < other.launch_time

    def __le__(self, other):
        return self.launch_time <= other.launch_time

    def __gt__(self, other):
        return self.launch_time > other.launch_time

    def __ge__(self, other):
        return self.launch_time >= other.launch_time


class LiveReplaysWidgetHandler:
    def __init__(self, liveTree, client, gameset):
        self.liveTree = liveTree
        self.liveTree.itemDoubleClicked.connect(self.liveTreeDoubleClicked)
        self.liveTree.itemPressed.connect(self.liveTreePressed)
        self.liveTree.header().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents,
        )
        self.liveTree.header().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.Stretch,
        )
        self.liveTree.header().setSectionResizeMode(
            2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents,
        )

        self.client = client
        self.gameset = gameset
        self.gameset.newLiveGame.connect(self._newGame)
        self._addExistingGames(gameset)

        self.games = {}

    def liveTreePressed(self, item):
        if QtWidgets.QApplication.mouseButtons() != QtCore.Qt.MouseButton.RightButton:
            return

        if self.liveTree.indexOfTopLevelItem(item) != -1:
            item.setExpanded(True)
            return

        menu = QtWidgets.QMenu(self.liveTree)

        # Actions for Games and Replays
        actionReplay = QtGui.QAction("Replay in FA", menu)
        actionLink = QtGui.QAction("Copy Link", menu)

        # Adding to menu
        menu.addAction(actionReplay)
        menu.addAction(actionLink)

        # Triggers
        actionReplay.triggered.connect(
            lambda: self.liveTreeDoubleClicked(item),
        )
        actionLink.triggered.connect(
            lambda: QtWidgets.QApplication.clipboard().setText(
                item.toolTip(0),
            ),
        )

        # Adding to menu
        menu.addAction(actionReplay)
        menu.addAction(actionLink)

        # Finally: Show the popup
        menu.popup(QtGui.QCursor.pos())

    def liveTreeDoubleClicked(self, item):
        """
        This slot launches a live replay from eligible items in liveTree
        """

        if item.isDisabled():
            return

        if (
            self.client.games.party
            and self.client.games.party.member_count > 1
        ):
            if not self.client.games.leave_party():
                return

        if self.liveTree.indexOfTopLevelItem(item) == -1:
            # Notify other modules that we're watching a replay
            self.client.viewing_replay.emit(item.gurl)
            replay(item.gurl)

    def _addExistingGames(self, gameset):
        for game in gameset.values():
            if game.state == GameState.PLAYING:
                self._newGame(game)

    def _newGame(self, game):
        item = LiveReplayItem(game)
        self.games[game] = item
        self.liveTree.insertTopLevelItem(0, item)
        game.updated.connect(self._check_game_closed)

    def _check_game_closed(self, game):
        if game.state == GameState.CLOSED:
            game.updated.disconnect(self._check_game_closed)
            self._removeGame(game)

    def _removeGame(self, game):
        self.liveTree.takeTopLevelItem(
            self.liveTree.indexOfTopLevelItem(self.games[game]),
        )
        del self.games[game]


class ReplayMetadata:
    def __init__(self, data: str) -> None:
        self.raw_data = data
        self.is_broken = False
        self.model: MetadataModel | None = None

        try:
            json_data = json.loads(data)
        except json.decoder.JSONDecodeError:
            self.is_broken = True
            return

        try:
            self.model = MetadataModel(**json_data)
        except ValidationError:
            self.is_broken = True

    @property
    def is_incomplete(self) -> bool:
        if self.model is None:
            return True
        return not self.model.complete

    def launch_time(self) -> float:
        if self.model.launched_at > 0:
            return self.model.launched_at
        return self.model.game_time


class LocalReplayItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, replay_file, metadata=None):
        QtWidgets.QTreeWidgetItem.__init__(self)
        self._replay_file = replay_file
        self._metadata = metadata
        self._map_dl_request = DownloadRequest()
        self._map_dl_request.done.connect(self._map_preview_downloaded)
        self._setup_appearance()

    def replay_path(self):
        return os.path.join(util.REPLAY_DIR, self._replay_file)

    def _setup_appearance(self):
        if self._metadata is None:
            self._setup_no_metadata_appearance()
        elif self._metadata.is_broken:
            self._setup_broken_appearance()
        elif self._metadata.is_incomplete:
            self._setup_incomplete_appearance()
        else:
            self._setup_complete_appearance()

    def _setup_no_metadata_appearance(self):
        self.setText(1, self._replay_file)
        self.setIcon(0, util.THEME.icon("replays/replay.png"))
        colors = client.instance.player_colors
        self.setForeground(0, QtGui.QColor(colors.get_color("default")))

    def _setup_broken_appearance(self):
        self.setIcon(0, util.THEME.icon("replays/broken.png"))
        self.setText(1, self._replay_file)
        # FIXME: Needs to come from theme
        self.setForeground(1, QtGui.QColor("red"))
        self.setForeground(2, QtGui.QColor("gray"))

        self.setText(2, "(replay parse error)")

    def _setup_incomplete_appearance(self):
        self.setIcon(0, util.THEME.icon("replays/replay.png"))
        self.setText(1, self._replay_file)
        self.setText(2, "(replay doesn't have complete metadata)")
        # FIXME: Needs to come from theme
        self.setForeground(1, QtGui.QColor("yellow"))

    def _setup_complete_appearance(self) -> None:
        data = self._metadata.model
        launch_time = time.localtime(self._metadata.launch_time())
        try:
            game_time = time.strftime("%H:%M", launch_time)
        except ValueError:
            game_time = "Unknown"

        icon = fa.maps.preview(data.mapname)
        if icon:
            self.setIcon(0, icon)
        else:
            dler = client.instance.map_preview_downloader
            dler.download_preview(data.mapname, self._map_dl_request)
            self.setIcon(0, util.THEME.icon("games/unknown_map.png"))

        self.setToolTip(0, fa.maps.getDisplayName(data.mapname))
        self.setText(0, game_time)
        self.setForeground(
            0,
            QtGui.QColor(client.instance.player_colors.get_color("default")),
        )
        self.setText(1, data.title)
        self.setToolTip(1, self._replay_file)

        playerlist = []
        for players in data.teams.values():
            playerlist.extend(players)
        self.setText(2, ", ".join(playerlist))
        self.setToolTip(2, ", ".join(playerlist))

        self.setText(3, data.featured_mod)
        self.setTextAlignment(3, QtCore.Qt.AlignmentFlag.AlignCenter)

    def replay_bucket(self):
        if self._metadata is None:
            return "legacy"
        if self._metadata.is_broken:
            return "broken"
        if self._metadata.is_incomplete:
            return "incomplete"
        try:
            t = time.localtime(self._metadata.launch_time())
            return time.strftime("%Y-%m-%d", t)
        except ValueError:
            return "broken"

    def _map_preview_downloaded(self):
        self._setup_appearance()


class LocalReplayBucketItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, kind, children):
        QtWidgets.QTreeWidgetItem.__init__(self)
        self._setup_appearance(kind, children)

    def _setup_appearance(self, kind, children):
        if kind == "broken":
            self._setup_broken_appearance()
        elif kind == "incomplete":
            self._setup_incomplete_appearance()
        elif kind == "legacy":
            self._setup_legacy_appearance()
        else:
            self._setup_date_appearance()

        self.setIcon(0, util.THEME.icon("replays/bucket.png"))
        self.setText(0, kind)
        self.setText(3, f"{len(children)} replays")
        self.setForeground(
            3,
            QtGui.QColor(client.instance.player_colors.get_color("default")),
        )

        for item in children:
            self.addChild(item)

    def _setup_broken_appearance(self):
        # FIXME: Needs to come from theme
        self.setForeground(0, QtGui.QColor("red"))

        self.setText(1, "(not watchable)")
        self.setForeground(
            1,
            QtGui.QColor(client.instance.player_colors.get_color("default")),
        )

    def _setup_incomplete_appearance(self):
        # FIXME: Needs to come from theme
        self.setForeground(0, QtGui.QColor("yellow"))

        self.setText(1, "(watchable)")
        self.setForeground(
            1,
            QtGui.QColor(client.instance.player_colors.get_color("default")),
        )

    def _setup_legacy_appearance(self):
        self.setForeground(
            0,
            QtGui.QColor(client.instance.player_colors.get_color("default")),
        )
        self.setForeground(
            1,
            QtGui.QColor(client.instance.player_colors.get_color("default")),
        )
        self.setText(1, "(old replay system)")

    def _setup_date_appearance(self):
        self.setForeground(
            0,
            QtGui.QColor(client.instance.player_colors.get_color("player")),
        )


class LocalReplaysWidgetHandler:
    def __init__(self, myTree: QTreeWidget) -> None:
        self.myTree = myTree
        self.myTree.itemDoubleClicked.connect(self.myTreeDoubleClicked)
        self.myTree.itemPressed.connect(self.my_tree_pressed)
        self.myTree.header().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents,
        )
        self.myTree.header().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents,
        )
        self.myTree.header().setSectionResizeMode(
            2, QtWidgets.QHeaderView.ResizeMode.Stretch,
        )
        self.myTree.header().setSectionResizeMode(
            3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents,
        )
        self.myTree.modification_time = 0

        replay_cache = os.path.join(util.CACHE_DIR, "local_replays_metadata")
        self.replay_files = LocalReplayMetadataCache(
            util.REPLAY_DIR, replay_cache,
        )

    def my_tree_pressed(self, item: LocalReplayItem) -> None:
        if QtWidgets.QApplication.mouseButtons() != QtCore.Qt.MouseButton.RightButton:
            return

        if item.isDisabled():
            return

        if self.myTree.indexOfTopLevelItem(item) != -1:
            return

        menu = QtWidgets.QMenu(self.myTree)

        # Actions for Games and Replays
        actionReplay = QtGui.QAction("Replay", menu)
        actionExplorer = QtGui.QAction("Show in Explorer", menu)
        actionDetails = QtGui.QAction("Details", menu)

        # Adding to menu
        menu.addAction(actionReplay)
        menu.addAction(actionExplorer)
        menu.addAction(actionDetails)

        # Triggers
        actionReplay.triggered.connect(lambda: self.myTreeDoubleClicked(item))
        actionExplorer.triggered.connect(
            lambda: util.showFileInFileBrowser(item.replay_path()),
        )
        actionDetails.triggered.connect(lambda: self.show_replay_details(item.replay_path()))

        # Finally: Show the popup
        menu.popup(QtGui.QCursor.pos())

    def show_replay_details(self, replay_path: str) -> None:
        replay_details = ReplayDetailsCard()
        replay_details.replay(replay_path)
        replay_details.exec()
        replay_details.deleteLater()

    def myTreeDoubleClicked(self, item):
        if item.isDisabled():
            return

        if self.myTree.indexOfTopLevelItem(item) == -1:
            replay(item.replay_path())

    def updatemyTree(self):
        modification_time = os.path.getmtime(util.REPLAY_DIR)
        if self.myTree.modification_time == modification_time:
            return  # nothing changed -> don't redo
        self.myTree.modification_time = modification_time
        self.myTree.clear()

        # We put the replays into buckets by day first, then we add them to the
        # treewidget.
        buckets = {}

        if not self.replay_files.cache_loaded:
            self.replay_files.load_cache()

        # Iterate
        for infile in os.listdir(util.REPLAY_DIR):
            if infile.endswith(".scfareplay"):
                metadata = None
            elif infile.endswith(".fafreplay"):
                metadata = self.replay_files[infile]
            else:
                continue
            item = LocalReplayItem(infile, metadata)
            bucket = item.replay_bucket()
            buckets.setdefault(bucket, [])
            buckets[bucket].append(item)

        self.replay_files.save_cache()
        # Now, create a top level treeWidgetItem for every bucket, and put the
        # bucket's contents into them
        for bucket, items in buckets.items():
            bucket_item = LocalReplayBucketItem(bucket, items)
            self.myTree.addTopLevelItem(bucket_item)


class LocalReplayMetadataCache:
    CACHE_DIFF_THRESHOLD = 20

    def __init__(self, cache_dir, cache_file):
        self._cache_dir = cache_dir
        self._cache_file = cache_file
        self._cache = {}
        self._new_cache_entries = set()
        self._used_cache_entries = set()
        self.cache_loaded = False

    def load_cache(self):
        if os.path.exists(self._cache_file):
            with open(self._cache_file) as fh:
                for line in fh:
                    filename, metadata = line.split(':', 1)
                    self._cache[filename] = ReplayMetadata(metadata)
        self.cache_loaded = True

    def save_cache(self):
        if not self._cache_differs_much_from_files():
            return
        with open(self._cache_file, "w") as fh:
            for filename in self._used_cache_entries:
                fh.write(filename + ":" + self._cache[filename].raw_data)

    def _cache_differs_much_from_files(self):
        new_entries = len(self._new_cache_entries)
        all_entries = len(self._cache)
        all_used_entries = len(self._used_cache_entries)
        unused_entries = all_entries - all_used_entries
        return new_entries + unused_entries > self.CACHE_DIFF_THRESHOLD

    def __getitem__(self, filename):
        if filename not in self._cache:
            try:
                target_file = os.path.join(self._cache_dir, filename)
                with open(target_file) as fh:
                    metadata = fh.readline()
                    self._cache[filename] = ReplayMetadata(metadata)
                self._new_cache_entries.add(filename)
            except OSError:
                raise KeyError

        self._used_cache_entries.add(filename)
        return self._cache[filename]


class ReplayVaultWidgetHandler:
    # connect to save/restore persistence settings for checkboxes & search
    # parameters
    automatic = Settings.persisted_property(
        "replay/automatic", default_value=False, type=bool,
    )
    spoiler_free = Settings.persisted_property(
        "replay/spoilerFree", default_value=True, type=bool,
    )
    hide_unranked = Settings.persisted_property(
        "replay/hideUnranked", default_value=False, type=bool,
    )
    match_username = Settings.persisted_property(
        "replay/matchUsername", default_value=True, type=bool,
    )

    def __init__(self, widget, dispatcher, client, gameset, playerset):
        self._w = widget
        self._dispatcher = dispatcher
        self.client = client
        self.client.authorized.connect(self.on_authorized)
        self._gameset = gameset
        self._playerset = playerset

        self.onlineReplays = {}
        self.selectedReplay = None
        self.apiConnector = ReplaysApiConnector()
        self.apiConnector.data_ready.connect(self.process_replays_data)

        self.leaderboard_api = LeaderboardApiConnector()
        self.leaderboard_api.data_ready.connect(self.process_leaderboards)

        self.replayDownload = QNetworkAccessManager()
        self.replayDownload.finished.connect(self.onDownloadFinished)
        self.toolboxHandler = ReplayToolboxHandler(
            self, widget, dispatcher, client, gameset, playerset,
        )

        self.showLatest = True
        self.searching = False
        self.searchInfo = "Searching..."
        self.defaultSearchParams = {
            "page[number]": 1,
            "page[size]": 100,
            "sort": "-startTime",
            "include": (
                "featuredMod,mapVersion,mapVersion.map,playerStats,"
                "playerStats.player,playerStats.ratingChanges"
            ),
        }

        _w = self._w
        _w.onlineTree.setItemDelegate(ReplayItemDelegate(_w))
        _w.onlineTree.itemDoubleClicked.connect(self.onlineTreeDoubleClicked)
        _w.onlineTree.itemPressed.connect(self.online_tree_clicked)

        _w.searchButton.pressed.connect(self.searchVault)
        _w.playerName.returnPressed.connect(self.searchVault)
        _w.mapName.returnPressed.connect(self.searchVault)
        _w.automaticCheckbox.stateChanged.connect(self.automaticCheckboxchange)
        _w.matchUsernameCheckbox.stateChanged.connect(
            self.matchUsernameCheckboxChange,
        )
        _w.showLatestCheckbox.stateChanged.connect(
            self.showLatestCheckboxchange,
        )
        _w.spoilerCheckbox.checkStateChanged.connect(self.spoiler_checkbox_change)
        _w.hideUnrCheckbox.stateChanged.connect(self.hideUnrCheckboxchange)
        _w.RefreshResetButton.pressed.connect(self.resetRefreshPressed)

        # restore persistent checkbox settings
        _w.matchUsernameCheckbox.setChecked(self.match_username)
        _w.automaticCheckbox.setChecked(self.automatic)
        _w.spoilerCheckbox.setChecked(self.spoiler_free)
        _w.hideUnrCheckbox.setChecked(self.hide_unranked)
        _w.detailsButton.clicked.connect(self.show_replay_details)
        _w.detailsButton.setVisible(False)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.stopSearchVault)

    def show_replay_details(self) -> None:
        item = self._w.onlineTree.currentItem()
        if item is not None and hasattr(item, "url"):
            replay_details = ReplayDetailsCard()
            replay_details.download_by_url(QtCore.QUrl(item.url))
            replay_details.exec()
            replay_details.deleteLater()

    def on_authorized(self) -> None:
        if self._w.leaderboardList.count() == 1:
            self.refresh_leaderboards()

    def refresh_leaderboards(self) -> None:
        while self._w.leaderboardList.count() != 1:
            self._w.leaderboardList.removeItem(1)
        self.leaderboard_api.requestData()

    def showToolTip(self, widget, msg):
        """
        Default tooltips are too slow and disappear when user starts typing
        """

        position = widget.mapToGlobal(
            QtCore.QPoint(0 + widget.width(), 0 - widget.height() / 2),
        )
        QtWidgets.QToolTip.showText(position, msg)

    def stopSearchVault(self):
        self.searching = False
        self._w.searchInfoLabel.clear()
        self._w.advSearchInfoLabel.clear()
        self.timer.stop()

    def searchVault(
        self,
        minRating: int | None = None,
        mapName: str | None = None,
        playerName: str | None = None,
        leaderboardListItemIndex: int | None = None,
        modListIndex: int | None = None,
        quantity: int | None = None,
        reset: bool | None = None,
        exactPlayerName: bool | None = None,
    ):
        w = self._w
        timePeriod = None

        if self.searching:
            QtWidgets.QMessageBox.critical(
                None,
                "Replay vault",
                "Please, wait for previous search to finish.",
            )
            return

        if reset:
            w.minRating.setValue(0)
            w.mapName.setText("")
            w.playerName.setText("")
            w.leaderboardList.setCurrentIndex(0)
            w.modList.setCurrentIndex(0)
            w.quantity.setValue(100)
            w.showLatestCheckbox.setChecked(True)
        else:
            if minRating is not None:
                w.minRating.setValue(minRating)
            if mapName is not None:
                w.mapName.setText(mapName)
            if playerName is not None:
                w.playerName.setText(playerName)
            if leaderboardListItemIndex is not None:
                w.leaderboardList.setCurrentIndex(leaderboardListItemIndex)
            if modListIndex is not None:
                w.modList.setCurrentIndex(modListIndex)
            if quantity is not None:
                w.quantity.setValue(quantity)
            if not self.showLatest:
                timePeriod = []
                timePeriod.append(
                    w.dateStart.dateTime().toUTC().toString(QtCore.Qt.DateFormat.ISODate),
                )
                timePeriod.append(
                    w.dateEnd.dateTime().toUTC().toString(QtCore.Qt.DateFormat.ISODate),
                )

        filters = self.prepareFilters(
            w.minRating.value(),
            w.mapName.text(),
            w.playerName.text(),
            w.leaderboardList.currentData(),
            w.modList.currentText(),
            timePeriod,
            exactPlayerName,
        )

        # """ search for some replays """
        self._w.onlineTree.clear()
        self._w.searchInfoLabel.setText(self.searchInfo)
        self._w.searchInfoLabel.setVisible(True)
        self._w.advSearchInfoLabel.setVisible(False)
        self.searching = True

        parameters = self.defaultSearchParams.copy()
        parameters["page[size]"] = w.quantity.value()

        if filters:
            parameters["filter"] = filters

        self.apiConnector.requestData(parameters, self.on_api_request_error)
        self.timer.start(90000)

    def prepareFilters(
        self,
        minRating: int | None,
        mapName: str | None,
        playerName: str | None,
        leaderboardName: str | None,
        modListIndex: int | None,
        timePeriod: list[str] | None = None,
        exactPlayerName: bool | None = None,
    ):
        '''
        Making filter string here + some logic to exclude "heavy" requests
        which may overload database (>30 sec searches). It might looks weak
        (and probably it is), but hey, it works! =)
        '''

        filters = []

        if self.hide_unranked:
            filters.append('validity=="VALID"')

        if leaderboardName not in (None, "All"):
            filters.append(
                'playerStats.ratingChanges.leaderboard.technicalName=="{}"'
                .format(leaderboardName),
            )

        if minRating and minRating > 0:
            filters.append(
                'playerStats.ratingChanges.meanBefore=ge="{}"'
                .format(minRating + 300),
            )

        if mapName:
            filters.append(
                f'mapVersion.map.displayName=="*{mapName}*"',
            )

        if playerName:
            if self.match_username or exactPlayerName:
                filters.append(
                    f'playerStats.player.login=="{playerName}"',
                )
            else:
                filters.append(
                    f'playerStats.player.login=="*{playerName}*"',
                )

        if modListIndex and modListIndex != "All":
            filters.append(
                f'featuredMod.technicalName=="{modListIndex}"',
            )

        if timePeriod:
            filters.append(f'startTime=ge="{timePeriod[0]}"')
            filters.append(f'startTime=le="{timePeriod[1]}"')
        elif len(filters) > 0:
            months = 3
            if playerName:
                months = 6

            startTime = (
                QtCore.QDateTime.currentDateTimeUtc()
                .addMonths(-months)
                .toString(QtCore.Qt.DateFormat.ISODate)
            )
            filters.append(f'startTime=ge="{startTime}"')

        if len(filters) > 0:
            return "({})".format(";".join(filters))

        return None

    def reloadView(self):
        if not self.searching:
            # refresh on Tab change or only the first time
            if self.automatic or self.onlineReplays == {}:
                self.searchVault(reset=True)

    def clear_scoreboard(self) -> None:
        if (layout_item := self._w.replayScoreLayout.itemAt(0)) is not None:
            scoreboard = layout_item.widget()
            scoreboard.setParent(None)
            self._w.replayScoreLayout.removeWidget(scoreboard)
            self._w.detailsButton.setVisible(False)
            scoreboard.deleteLater()

    def adjust_scoreboard_size(self, width: int, height: int) -> None:
        self._w.replayScoreScrollArea.setMaximumWidth(width)
        self._w.replayScoreScrollArea.setMaximumHeight(height)

    def add_scoreboard(self, item: ReplayItem) -> None:
        self.clear_scoreboard()
        scoreboard = item.generate_scoreboard()
        self._w.replayScoreLayout.addWidget(scoreboard)
        self.adjust_scoreboard_size(scoreboard.width(), scoreboard.height())
        game_finished = hasattr(item, "duration") and "playing" not in item.duration
        available = item.game and item.game.replay_available
        self._w.detailsButton.setVisible(game_finished and available)

    def online_tree_clicked(self, item: ReplayItem | QTreeWidgetItem) -> None:
        if not isinstance(item, ReplayItem):
            return

        if QtWidgets.QApplication.mouseButtons() == QtCore.Qt.MouseButton.RightButton:
            item.pressed()
        else:
            self.selectedReplay = item
            self.add_scoreboard(item)
            if self.toolboxHandler.mapPreview:
                self.toolboxHandler.updateMapPreview()

    def onlineTreeDoubleClicked(self, item):
        if (
            self.client.games.party
            and self.client.games.party.member_count > 1
        ):
            if not self.client.games.leave_party():
                return

        if hasattr(item, "duration"):  # it's a game not a date separator
            if "playing" in item.duration:  # live game will not be in vault
                # search result isn't updated automatically - so game status
                # might have changed
                if item.uid in self._gameset:  # game still running
                    game = self._gameset[item.uid]
                    if not game.launched_at:  # we frown upon those
                        return
                    if game.has_live_replay:  # live game over 5min
                        for name in game.players:  # find a player ...
                            if name in self._playerset:  # still logged in
                                self._startReplay(name)
                                break
                    else:
                        delta = time.gmtime(
                            game.LIVE_REPLAY_DELAY_SECS
                            - (time.time() - game.launched_at),
                        )
                        wait_str = time.strftime('%M Min %S Sec', delta)
                        QtWidgets.QMessageBox.information(
                            client.instance,
                            "5 Minute Live Game Delay",
                            (
                                "It is too early to join the Game.\n"
                                "You have to wait {} to join.".format(wait_str)
                            ),
                        )
                else:  # game ended - ask to start replay
                    if QtWidgets.QMessageBox.question(
                        client.instance,
                        "Live Game ended",
                        "Would you like to watch the replay from the vault?",
                        QtWidgets.QMessageBox.StandardButton.Yes,
                        QtWidgets.QMessageBox.StandardButton.No,
                    ) == QtWidgets.QMessageBox.StandardButton.Yes:
                        req = QNetworkRequest(QtCore.QUrl(item.url))
                        self.replayDownload.get(req)

            else:  # start replay
                if hasattr(item, "url"):
                    req = QNetworkRequest(QtCore.QUrl(item.url))
                    self.replayDownload.get(req)

    def _startReplay(self, name):
        if name is None or name not in self._playerset:
            return
        player = self._playerset[name]

        if not player.currentGame:
            return
        replay(player.currentGame.url(player.id))

    def matchUsernameCheckboxChange(self, state):
        self.match_username = state

    def automaticCheckboxchange(self, state):
        self.automatic = state

    def spoiler_checkbox_change(self, state: QtCore.Qt.CheckState) -> None:
        self.spoiler_free = state == QtCore.Qt.CheckState.Checked
        # if something is selected in the tree to the left
        if self.selectedReplay:
            # and if it is a game
            if isinstance(self.selectedReplay, ReplayItem):
                # then we redo it
                self.add_scoreboard(self.selectedReplay)

    def showLatestCheckboxchange(self, state):
        self.showLatest = state
        if state:  # disable date edit fields if True
            self._w.dateStart.setEnabled(False)
            self._w.dateEnd.setEnabled(False)
        else:  # enable date edit and set current date
            self._w.dateStart.setEnabled(True)
            self._w.dateEnd.setEnabled(True)

            date = QtCore.QDate.currentDate()
            self._w.dateStart.setDate(date)
            self._w.dateEnd.setDate(date)

    def hideUnrCheckboxchange(self, state):
        self.hide_unranked = state

    def resetRefreshPressed(self):
        # reset search parameter and reload recent Replays List
        if not self.searching:
            self.searchVault(reset=True)

    def onDownloadFinished(self, reply):
        if reply.error() != QNetworkReply.NetworkError.NoError:
            QtWidgets.QMessageBox.warning(
                self._w, "Network Error", reply.errorString(),
            )
        else:
            faf_replay = QtCore.QFile(
                os.path.join(util.CACHE_DIR, "temp.fafreplay"),
            )
            faf_replay.open(
                QtCore.QIODevice.OpenModeFlag.WriteOnly
                | QtCore.QIODevice.OpenModeFlag.Truncate,
            )
            faf_replay.write(reply.readAll())
            faf_replay.flush()
            faf_replay.close()
            replay(os.path.join(util.CACHE_DIR, "temp.fafreplay"))

    def on_api_request_error(self, reply: QNetworkReply) -> None:
        self.stopSearchVault()
        self._w.searchInfoLabel.setText(reply.errorString())

    def process_replays_data(self, message: dict) -> None:
        self.stopSearchVault()
        self.clear_scoreboard()
        self.onlineReplays = {}
        replays = message["data"]
        for replay_item in replays:
            uid = int(replay_item["id"])
            if uid not in self.onlineReplays:
                self.onlineReplays[uid] = ReplayItem(uid, self._w)
            self.onlineReplays[uid].update(replay_item, self.client)
        self.update_online_tree()

        if len(message["data"]) == 0:
            self._w.searchInfoLabel.setText("No replays found")
            self._w.advSearchInfoLabel.setText("No replays found")

    def process_leaderboards(self, message: dict[str, list[Leaderboard]]) -> None:
        for leaderboard in message["values"]:
            self._w.leaderboardList.addItem(leaderboard.pretty_name, leaderboard.technical_name)

    def update_online_tree(self) -> None:
        self.selectedReplay = None  # clear, it won't be part of the new tree
        self.clear_scoreboard()
        self._w.onlineTree.clear()
        buckets = {}
        for uid in self.onlineReplays:
            bucket = buckets.setdefault(self.onlineReplays[uid].startDate, [])
            bucket.append(self.onlineReplays[uid])

        for bucket in buckets.keys():
            bucket_item = QtWidgets.QTreeWidgetItem()
            self._w.onlineTree.addTopLevelItem(bucket_item)

            bucket_item.setIcon(0, util.THEME.icon("replays/bucket.png"))
            bucket_item.setText(
                0, f"<font color='white'>{bucket}</font>",
            )
            bucket_len = len(buckets[bucket])
            bucket_item.setText(
                1, f"<font color='white'>{bucket_len} replays</font>",
            )

            for replay_item in buckets[bucket]:
                bucket_item.addChild(replay_item)
                replay_item.setFirstColumnSpanned(True)
                replay_item.setIcon(0, replay_item.thumbnail)

            bucket_item.setExpanded(True)


class ReplaysWidget(BaseClass, FormClass):
    def __init__(self, client, dispatcher, gameset, playerset):
        super(BaseClass, self).__init__()

        self.setupUi(self)

        self.liveManager = LiveReplaysWidgetHandler(
            self.liveTree, client, gameset,
        )
        self.localManager = LocalReplaysWidgetHandler(self.myTree)
        self.vaultManager = ReplayVaultWidgetHandler(
            self, dispatcher, client, gameset, playerset,
        )

        logger.info("Replays Widget instantiated.")

    def refresh_leaderboards(self) -> None:
        self.vaultManager.refresh_leaderboards()

    def set_player(self, name: str) -> None:
        self.setCurrentIndex(2)  # focus on Online Fault
        self.vaultManager.searchVault(0, "", name, 0, 0, 100, exactPlayerName=True)

    def focusEvent(self, event):
        self.localManager.updatemyTree()
        self.vaultManager.reloadView()
        return BaseClass.focusEvent(self, event)

    def showEvent(self, event):
        self.localManager.updatemyTree()
        self.vaultManager.reloadView()
        return BaseClass.showEvent(self, event)
