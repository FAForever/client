import json
import logging
import os
import re
import time
from enum import IntEnum
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from pydantic import ValidationError
from PyQt6 import QtCore
from PyQt6 import QtGui
from PyQt6 import QtWidgets
from PyQt6.QtNetwork import QNetworkAccessManager
from PyQt6.QtNetwork import QNetworkReply
from PyQt6.QtNetwork import QNetworkRequest
from PyQt6.QtWidgets import QStyle
from PyQt6.QtWidgets import QTreeWidget
from PyQt6.QtWidgets import QTreeWidgetItem

from src import client
from src import fa
from src import util
from src.api.ApiAccessors import ParsedDataApiResponse
from src.api.models.Leaderboard import Leaderboard
from src.api.replaysapi import ReplaysApiConnector
from src.api.stats_api import LeaderboardApiConnector
from src.client.connection import Dispatcher
from src.config import Settings
from src.downloadManager import DownloadRequest
from src.fa.replay import WatchedReplaysTracker
from src.fa.replay import replay
from src.model.game import Game
from src.model.game import GameState
from src.model.game import GameType
from src.model.gameset import Gameset
from src.model.playerset import Playerset
from src.qt.utils import qpainter
from src.replays.models import MetadataModel
from src.replays.replaydetails.replaycard import ReplayDetailsCard
from src.replays.replayitem import ReplayItem
from src.replays.replayitem import ReplayItemDelegate
from src.replays.replayToolbox import ReplayToolboxHandler
from src.util.gameurl import GameUrl
from src.util.gameurl import GameUrlType

if TYPE_CHECKING:
    from src.client._clientwindow import ClientWindow

logger = logging.getLogger(__name__)

# Replays uses the new Inheritance Based UI creation pattern
# This allows us to do all sorts of awesome stuff by overriding methods etc.

FormClass, BaseClass = util.THEME.loadUiType("replays/replays.ui")


class LiveReplayItem(QtWidgets.QTreeWidgetItem):
    class Columns(IntEnum):
        (
            MAP,
            START_TIME,
            TITLE,
            HOST,
            AVG_RATING,
            PLAYERS,
            MAX_PLAYERS,
            MODS,
            FEATURED_MOD,
        ) = range(9)

    LIVEREPLAY_DELAY = 5 * 60

    def __init__(self, game: Game) -> None:
        QtWidgets.QTreeWidgetItem.__init__(self)
        self._game = game
        if game.launched_at is not None:
            self.launch_time = game.launched_at
        else:
            self.launch_time = time.time()
        self._map_dl_request = DownloadRequest()
        self._map_dl_request.done.connect(self._map_preview_downloaded)

        self._game.updated.connect(self._update_game)
        self._update_game(self._game)
        self._filtered_out = False

    def set_filtered_out(self, filtered: bool, /) -> None:
        self._filtered_out = filtered
        self.setHidden(filtered or self._delayed)

    def set_show_delay(self) -> None:
        if time.time() - self.launch_time < self.LIVEREPLAY_DELAY:
            self.setHidden(True)
            # Wait until the replayserver makes the replay available
            elapsed_time = time.time() - self.launch_time
            delay_time = self.LIVEREPLAY_DELAY - elapsed_time
            QtCore.QTimer.singleShot(int(1000 * delay_time), self._show_item)
            self._delayed = True
        else:
            self._delayed = False

    def _show_item(self):
        self._delayed = False
        self.setHidden(self._filtered_out)

    def _map_preview_downloaded(self, preview_file: str, pixmap: QtGui.QPixmap) -> None:
        if util.pretty_decoded_basename(preview_file) != self._game.mapname:
            return
        self.setIcon(0, QtGui.QIcon(pixmap))

    def _update_game(self, game: Game) -> None:
        if game.state == GameState.CLOSED:
            return

        self.takeChildren()     # Clear the children of this item
        self._set_debug_tooltip(game)
        self._set_game_map_icon(game)
        self._set_misc_formatting(game)
        self._set_color(game)
        self._generate_player_subitems(game)

    def _set_debug_tooltip(self, game: Game) -> None:
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

    def _set_misc_formatting(self, game: Game) -> None:
        self.setToolTip(0, fa.maps.getDisplayName(game.mapname))

        time_fmt = "%Y-%m-%d  -  %H:%M"
        launch_time = time.strftime(time_fmt, time.localtime(self.launch_time))
        self.setText(self.Columns.START_TIME, launch_time)

        colors = client.instance.player_colors
        self.setForeground(self.Columns.START_TIME, QtGui.QColor(colors.get_color("default")))
        self.setForeground(self.Columns.TITLE, QtGui.QColor(colors.get_color("player")))
        self.setText(self.Columns.TITLE, game.title)
        self.setToolTip(self.Columns.TITLE, game.title)
        self.setText(self.Columns.HOST, game.host)
        self.setText(self.Columns.AVG_RATING, f"{game.average_rating:.0f}")
        self.setTextAlignment(self.Columns.AVG_RATING, QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setText(self.Columns.PLAYERS, str(len(game.playing_players)))
        self.setTextAlignment(self.Columns.PLAYERS, QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setText(self.Columns.MAX_PLAYERS, str(game.max_players))
        self.setTextAlignment(self.Columns.MAX_PLAYERS, QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setText(self.Columns.MODS, ",".join(game.sim_mods.values()))
        self.setToolTip(self.Columns.MODS, "\n".join(game.sim_mods.values()))
        self.setText(self.Columns.FEATURED_MOD, game.featured_mod)
        self.setTextAlignment(self.Columns.FEATURED_MOD, QtCore.Qt.AlignmentFlag.AlignCenter)

    def _is_me(self, name):
        return client.instance.login == name

    def _is_friend(self, name: str) -> bool:
        playerid = client.instance.players.getID(name)
        return client.instance.user_relations.model.is_friend(playerid)

    def _is_online(self, name: str) -> bool:
        return client.instance.players.get_by_name(name) is not None

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
        self.setForeground(self.Columns.TITLE, QtGui.QColor(colors.get_color(my_color)))

    def _generate_player_subitems(self, game):
        if not game.teams:
            self.setDisabled(True)
            return
        for player in game.playing_players:  # observers don't stream replays
            playeritem = self._create_playeritem(game, player)
            self.addChild(playeritem)

    def _create_playeritem(self, game, name):
        item = QtWidgets.QTreeWidgetItem()
        item.setText(1, name)

        if self._is_me(name):
            player_color = "self"
        elif self._is_friend(name):
            player_color = "friend"
        elif self._is_online(name):
            player_color = "player"
        else:
            player_color = "default"
        colors = client.instance.player_colors
        item.setForeground(1, QtGui.QColor(colors.get_color(player_color)))

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

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, LiveReplayItem):
            return NotImplemented
        match self.treeWidget().sortColumn():
            case self.Columns.MAP:
                return self._game.mapname < other._game.mapname
            case self.Columns.START_TIME:
                return self.launch_time < other.launch_time
            case self.Columns.TITLE:
                return self._game.title < other._game.title
            case self.Columns.HOST:
                return self._game.host < other._game.host
            case self.Columns.AVG_RATING:
                return self._game.average_rating < other._game.average_rating
            case self.Columns.PLAYERS:
                return len(self._game.playing_players) < len(other._game.playing_players)
            case self.Columns.MAX_PLAYERS:
                return self._game.max_players < other._game.max_players
            case self.Columns.MODS:
                return len(self._game.sim_mods) < len(other._game.sim_mods)
            case self.Columns.FEATURED_MOD:
                return self._game.featured_mod < other._game.featured_mod
            case _:
                return self.launch_time < other.launch_time


class LiveReplaysWidgetHandler:
    def __init__(self, liveTree, client, gameset, live_tree_filters, splitter):
        self.liveTree = liveTree
        self.liveTree.itemDoubleClicked.connect(self.liveTreeDoubleClicked)
        self.liveTree.itemPressed.connect(self.liveTreePressed)
        self.liveTree.sortByColumn(
            LiveReplayItem.Columns.START_TIME, QtCore.Qt.SortOrder.DescendingOrder,
        )
        self.liveTree.header().setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        for column in LiveReplayItem.Columns:
            if column in (LiveReplayItem.Columns.TITLE, LiveReplayItem.Columns.MODS):
                self.liveTree.header().setSectionResizeMode(
                    column, QtWidgets.QHeaderView.ResizeMode.Stretch,
                )
            else:
                self.liveTree.header().setSectionResizeMode(
                    column, QtWidgets.QHeaderView.ResizeMode.ResizeToContents,
                )
        self.liveTree.setAlternatingRowColors(True)
        self.game_type_filter = live_tree_filters[0]
        self.game_type_filter.addItems(typ.value for typ in GameType)
        self.game_type_filter.currentIndexChanged.connect(self.filter_games)

        self.max_players_filter = live_tree_filters[1]
        self.max_players_filter.addItems(map(str, range(1, 17)))
        self.max_players_filter.currentIndexChanged.connect(self.filter_games)

        self.num_players_filter = live_tree_filters[2]
        self.num_players_filter.addItems(map(str, range(1, 17)))
        self.num_players_filter.currentIndexChanged.connect(self.filter_games)

        self.featured_mod_filter = live_tree_filters[3]
        self.featured_mod_filter.currentIndexChanged.connect(self.filter_games)
        self.modded_games_filter = live_tree_filters[4]
        self.modded_games_filter.checkStateChanged.connect(self.filter_games)

        self.client = client
        self.gameset = gameset
        self.gameset.newLiveGame.connect(self._newGame)
        self._addExistingGames(gameset)

        self.splitter = splitter
        splitter_sizes = Settings.get_list("replay/live_splitter", type=int, default=[])
        if len(splitter_sizes) == 2:
            self.splitter.setSizes(splitter_sizes)
        self.splitter.splitterMoved.connect(self.on_splitter_moved)

        self.games = {}

    def on_splitter_moved(self) -> None:
        Settings.set("replay/live_splitter", self.splitter.sizes())

    def filter_games(self) -> None:
        self._filter_games()

    def _filter_games(self, count: int | None = None) -> None:
        game_type = self.game_type_filter.currentText()
        max_players = self.max_players_filter.currentText()
        num_players = self.num_players_filter.currentText()
        mod = self.featured_mod_filter.currentText()
        hide_modded = self.modded_games_filter.checkState() == QtCore.Qt.CheckState.Checked

        for i in range(count or self.liveTree.topLevelItemCount()):
            item = self.liveTree.topLevelItem(i)
            hide = any((
                game_type != "Any" and item._game.game_type.value != game_type,
                max_players != "Any" and item._game.max_players != int(max_players),
                num_players != "Any" and item._game.num_players != int(num_players),
                mod != "Any" and item._game.featured_mod != mod,
                hide_modded and item._game.sim_mods,
            ))
            item.set_filtered_out(hide)

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
            if not Settings.get("game/replay_process", True, type=bool):
                self.client.viewing_replay.emit(item.gurl)
            self.client.live_replay_streamer.start_live_replay(item.gurl)

    def _addExistingGames(self, gameset):
        for game in gameset.values():
            if game.state == GameState.PLAYING:
                self._newGame(game)

    def _newGame(self, game):
        item = LiveReplayItem(game)
        self.games[game] = item
        self.liveTree.insertTopLevelItem(0, item)
        item.set_show_delay()
        game.updated.connect(self._check_game_closed)
        self._filter_games(1)

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
    def __init__(self, replay_file: str, metadata: ReplayMetadata | None = None) -> None:
        super().__init__()
        self._replay_file = replay_file
        self._metadata = metadata
        self._map_dl_request = DownloadRequest()
        self._map_dl_request.done.connect(self._map_preview_downloaded)
        self._loaded = False

    @property
    def uid(self) -> int:
        if found := re.match(r"\d+", self._replay_file):
            return int(found[0])
        try:
            return self._metadata.model.uid  # type: ignore[attr-defined]
        except AttributeError:
            return -1

    def watched(self) -> bool:
        return self.uid in WatchedReplaysTracker

    def count_as_watched(self) -> bool:
        return Settings.get("replay/markWatched", True, type=bool) and self.watched()

    def change_watched_status(self) -> None:
        if self.watched():
            WatchedReplaysTracker.discard(self.uid)
        else:
            WatchedReplaysTracker.add(self.uid)

    def data(self, column: int, role: int = 0) -> Any:
        if role == QtCore.Qt.ItemDataRole.UserRole:
            return self
        return super().data(column, role)

    def replay_path(self):
        return os.path.join(util.REPLAY_DIR, self._replay_file)

    def _setup_appearance(self) -> None:
        if self._loaded:
            return

        if self._metadata is None:
            self._setup_no_metadata_appearance()
        elif self._metadata.is_broken:
            self._setup_broken_appearance()
        elif self._metadata.is_incomplete:
            self._setup_incomplete_appearance()
        else:
            self._setup_complete_appearance()

        self._loaded = True

    def _setup_no_metadata_appearance(self):
        self.setText(1, self._replay_file)
        self.setIcon(0, util.THEME.icon("replays/replay.png"))
        colors = client.instance.player_colors
        self.setForeground(0, QtGui.QColor(colors.get_color("default")))

    def _setup_broken_appearance(self):
        self.setIcon(0, util.THEME.icon("replays/broken.png"))
        self.setText(1, self._replay_file)
        time_color_str = util.THEME.find_stylesheet_attribute(
            "LocalReplayTreeItem::custom:broken",
            "time-color",
        )
        title_color_str = util.THEME.find_stylesheet_attribute(
            "LocalReplayTreeItem::custom:broken",
            "title-color",
        )
        self.setForeground(1, QtGui.QColor(time_color_str))
        self.setForeground(2, QtGui.QColor(title_color_str))
        self.setText(2, "(replay parse error)")

    def _setup_incomplete_appearance(self):
        self.setIcon(0, util.THEME.icon("replays/replay.png"))
        self.setText(1, self._replay_file)
        self.setText(2, "(replay doesn't have complete metadata)")
        color_str = util.THEME.find_stylesheet_attribute(
            "LocalReplayTreeItem::custom:incomplete",
            "time-color",
        )
        self.setForeground(1, QtGui.QColor(color_str))

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

    def data(self, column: int, role: int = 0) -> Any:
        if role == QtCore.Qt.ItemDataRole.UserRole:
            return self
        return super().data(column, role)

    def count_as_watched(self) -> bool:
        return all(self.child(i).count_as_watched() for i in range(self.childCount()))

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
        color_str = util.THEME.find_stylesheet_attribute(
            "LocalReplayBucketItem::custom:broken",
            "color",
        )
        self.setForeground(0, QtGui.QColor(color_str))

        self.setText(1, "(not watchable)")
        self.setForeground(
            1,
            QtGui.QColor(client.instance.player_colors.get_color("default")),
        )

    def _setup_incomplete_appearance(self):
        color_str = util.THEME.find_stylesheet_attribute(
            "LocalReplayBucketItem::custom:incomplete",
            "color",
        )
        self.setForeground(0, QtGui.QColor(color_str))

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


class LocalReplayItemDelegate(QtWidgets.QStyledItemDelegate):
    def paint(
        self,
        painter: QtGui.QPainter | None,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> None:
        if painter is None:
            return

        tree_item = cast(
            LocalReplayItem | LocalReplayBucketItem,
            index.data(QtCore.Qt.ItemDataRole.UserRole),
        )
        with qpainter(painter) as p:
            if (icon := index.data(QtCore.Qt.ItemDataRole.DecorationRole)) is not None:
                iconsize = icon.actualSize(option.rect.size())
                text_align = QtCore.Qt.AlignmentFlag.AlignCenter
                icon.paint(
                    p,
                    option.rect,
                    QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
                    icon.Mode.Disabled if tree_item.count_as_watched() else icon.Mode.Normal,
                )
            else:
                iconsize = QtCore.QSize(3, 0)
                text_align = QtCore.Qt.AlignmentFlag.AlignVCenter

            if tree_item.count_as_watched():
                factor = 300 if option.state & QStyle.StateFlag.State_MouseOver else 200
                brush = index.data(QtCore.Qt.ItemDataRole.ForegroundRole) or option.palette.text()
                p.setPen(brush.color().darker(factor))

            p.drawText(
                option.rect.adjusted(iconsize.width(), 0, 0, 0),
                index.data(QtCore.Qt.ItemDataRole.TextAlignmentRole) or text_align,
                index.data(),
            )


class LocalReplaysWidgetHandler:
    def __init__(self, myTree: QTreeWidget, client: ClientWindow) -> None:
        self.client = client
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
        self.myTree.setItemDelegate(LocalReplayItemDelegate(self.myTree))

        replay_cache = os.path.join(util.CACHE_DIR, "local_replays_metadata")
        self.replay_files = LocalReplayMetadataCache(
            util.REPLAY_DIR, replay_cache,
        )
        self.myTree.itemExpanded.connect(self.on_item_expanded)

    def on_item_expanded(self, item: LocalReplayBucketItem) -> None:
        for index in range(item.childCount()):
            cast(LocalReplayItem, item.child(index))._setup_appearance()

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
        actionMarkWatched = QtGui.QAction(
            f"Mark as {'unwatched' if item.watched() else 'watched'}",
            menu,
        )
        actionDetails = QtGui.QAction("Details", menu)

        # Adding to menu
        menu.addAction(actionReplay)
        menu.addAction(actionExplorer)
        menu.addAction(actionMarkWatched)
        menu.addAction(actionDetails)

        # Triggers
        actionReplay.triggered.connect(lambda: self.myTreeDoubleClicked(item))
        actionExplorer.triggered.connect(
            lambda: util.showFileInFileBrowser(item.replay_path()),
        )
        actionMarkWatched.triggered.connect(lambda: self.change_watched_status(item))
        actionDetails.triggered.connect(lambda: self.show_replay_details(item.replay_path()))

        # Finally: Show the popup
        menu.popup(QtGui.QCursor.pos())

    def change_watched_status(self, item: LocalReplayItem) -> None:
        item.change_watched_status()
        self.myTree.update()

    def show_replay_details(self, replay_path: str) -> None:
        replay_details = ReplayDetailsCard(self.client.map_generator, self.client)
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

    def __init__(self, cache_dir: str, cache_file: str) -> None:
        self._cache_dir = cache_dir
        self._cache_file = cache_file
        self._cache: dict[str, ReplayMetadata] = {}
        self._new_cache_entries: set[str] = set()
        self._used_cache_entries: set[str] = set()
        self.cache_loaded = False

    def load_cache(self) -> None:
        if os.path.exists(self._cache_file):
            with open(self._cache_file) as fh:
                for line in fh:
                    filename, metadata = line.split(':', 1)
                    self._cache[filename] = ReplayMetadata(metadata)
        self.cache_loaded = True

    def save_cache(self) -> None:
        if not self._cache_differs_much_from_files():
            return
        with open(self._cache_file, "w", newline="\n") as fh:
            for filename in self._used_cache_entries:
                fh.write(filename + ":" + self._cache[filename].raw_data)

    def _cache_differs_much_from_files(self) -> bool:
        new_entries = len(self._new_cache_entries)
        all_entries = len(self._cache)
        all_used_entries = len(self._used_cache_entries)
        unused_entries = all_entries - all_used_entries
        return new_entries + unused_entries > self.CACHE_DIFF_THRESHOLD

    def __getitem__(self, filename: str, /) -> ReplayMetadata:
        if filename not in self._cache:
            try:
                target_file = os.path.join(self._cache_dir, filename)
                with open(target_file, "rb") as fh:
                    metadata = fh.readline()
                self._cache[filename] = ReplayMetadata(metadata.decode())
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
    mark_watched = Settings.persisted_property("replay/markWatched", default_value=True, type=bool)

    def __init__(
        self,
        widget: ReplaysWidget,
        dispatcher: Dispatcher,
        client: ClientWindow,
        gameset: Gameset,
        playerset: Playerset,
    ) -> None:
        self._w = widget
        self._dispatcher = dispatcher
        self.client = client
        self.client.authorized.connect(self.on_authorized)
        self._gameset = gameset
        self._playerset = playerset

        self.onlineReplays = {}
        self.selectedReplay = None
        self.apiConnector = ReplaysApiConnector()

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

        # restore persistent checkbox settings
        _w.matchUsernameCheckbox.setChecked(self.match_username)
        _w.markWatchedCheckbox.setChecked(self.mark_watched)
        _w.automaticCheckbox.setChecked(self.automatic)
        _w.spoilerCheckbox.setChecked(self.spoiler_free)
        _w.hideUnrCheckbox.setChecked(self.hide_unranked)

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
        _w.markWatchedCheckbox.checkStateChanged.connect(self.mark_watched_change)

        _w.detailsButton.clicked.connect(self.show_replay_details)
        _w.detailsButton.setVisible(False)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.stopSearchVault)

        self.bucket_item_date_color = util.THEME.find_stylesheet_attribute(
            "ReplayBucketItemFormatter::custom",
            "color-date",
        )
        self.bucket_item_count_color = util.THEME.find_stylesheet_attribute(
            "ReplayBucketItemFormatter::custom",
            "color-count",
        )

    def show_replay_details(self) -> None:
        item = self._w.onlineTree.currentItem()
        if item is not None and hasattr(item, "url"):
            replay_details = ReplayDetailsCard(self.client.map_generator, self.client)
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

        self.apiConnector.get_parsed(
            parameters,
            self.process_replays_data,
            self.on_api_request_error,
        )
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
        game_finished = "playing" not in item.status
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

    def onlineTreeDoubleClicked(self, item: ReplayItem) -> None:
        if (
            self.client.games.party
            and self.client.games.party.member_count > 1
        ):
            if not self.client.games.leave_party():
                return

        if not hasattr(item, "duration") or item.duration is None:
            return

        if "playing" in item.status:  # live game will not be in vault
            # search result isn't updated automatically - so game status
            # might have changed
            if item.uid in self._gameset:  # game still running
                game = self._gameset[item.uid]
                if not game.launched_at:  # we frown upon those
                    return
                if game.has_live_replay:  # live game over 5min
                    for name in game.players:  # find a player ...
                        if self._playerset.get_by_name(name) is not None:  # still logged in
                            self._startReplay(name)
                            break
                else:
                    game.warn_live_delay(client.instance)
            elif item.replay["endTime"] is None:
                # player probably foed us; hiding started games from foes
                # makes no sense, but currently server does that
                name = item.replay["host"]["login"]
                url = GameUrl(
                    GameUrlType.LIVE_REPLAY,
                    item.mapname,
                    item.mod,
                    item.uid,
                    name,
                )
                self.client.live_replay_streamer.start_live_replay(url)
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

    def _startReplay(self, name: str | None) -> None:
        if (
            name is None
            or (player := self._playerset.get_by_name(name)) is None
            or player.currentGame is None
        ):
            return

        url = player.currentGame.url(player.id)
        self.client.live_replay_streamer.start_live_replay(url)

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

    def mark_watched_change(self, state: QtCore.Qt.CheckState) -> None:
        self.mark_watched = state == QtCore.Qt.CheckState.Checked
        self._w.onlineTree.update()

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

    def process_replays_data(self, message: ParsedDataApiResponse) -> None:
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

        for bucket, replay_items in buckets.items():
            bucket_item = QtWidgets.QTreeWidgetItem()
            self._w.onlineTree.addTopLevelItem(bucket_item)

            bucket_item.setIcon(0, util.THEME.icon("replays/bucket.png"))
            bucket_item.setText(
                0, f"<font color='{self.bucket_item_date_color}'>{bucket}</font>",
            )
            bucket_len = len(buckets[bucket])
            bucket_item.setText(
                1, f"<font color='{self.bucket_item_count_color}'>{bucket_len} replays</font>",
            )

            for replay_item in replay_items:
                bucket_item.addChild(replay_item)
                replay_item.setFirstColumnSpanned(True)
                replay_item.setIcon(0, replay_item.thumbnail)

            bucket_item.setExpanded(True)


class ReplaysWidget(BaseClass, FormClass):
    def __init__(
        self,
        client: ClientWindow,
        dispatcher: Dispatcher,
        gameset: Gameset,
        playerset: Playerset,
    ) -> None:
        BaseClass.__init__(self)
        self.setupUi(self)

        live_filters = [
            self.gameTypeComboBox,
            self.maxPlayersComboBox,
            self.numPlayersComboBox,
            self.featuredModComboBox,
            self.hideModdedCheckBox,
        ]
        self.liveManager = LiveReplaysWidgetHandler(
            self.liveTree,
            client,
            gameset,
            live_filters,
            self.liveReplaysWidgetSplitter,
        )
        self.localManager = LocalReplaysWidgetHandler(self.myTree, client)
        self.vaultManager = ReplayVaultWidgetHandler(self, dispatcher, client, gameset, playerset)
        self.currentChanged.connect(self.on_tab_changed)

        logger.info("Replays Widget instantiated.")

    def refresh_leaderboards(self) -> None:
        self.vaultManager.refresh_leaderboards()

    def set_player(self, name: str) -> None:
        self.setCurrentIndex(2)  # focus on Online Fault
        self.vaultManager.searchVault(0, "", name, 0, 0, 100, exactPlayerName=True)

    def focusEvent(self, event):
        if self.myTree.isVisible():
            self.localManager.updatemyTree()
        self.vaultManager.reloadView()
        return BaseClass.focusEvent(self, event)

    def showEvent(self, event):
        if self.myTree.isVisible():
            self.localManager.updatemyTree()
        self.vaultManager.reloadView()
        return BaseClass.showEvent(self, event)

    def on_tab_changed(self, index: int) -> None:
        if index == self.indexOf(self.localTab):
            self.localManager.updatemyTree()
