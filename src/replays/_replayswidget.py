from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from fa.replay import replay
from util.gameurl import GameUrl, GameUrlType
from config import Settings
import util
import os
import fa
import time
import client
import json
import jsonschema

from replays.replayitem import ReplayItem, ReplayItemDelegate
from model.game import GameState
from replays.connection import ReplaysConnection
from downloadManager import DownloadRequest

import logging
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
            QtCore.QTimer.singleShot(1000 * delay_time, self._show_item)

    def _show_item(self):
        self.setHidden(False)

    def _map_preview_downloaded(self, mapname, result):
        if mapname != self._game.mapname:
            return
        path, is_local = result
        icon = util.THEME.icon(path, is_local)
        self.setIcon(0, icon)

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
            tip += "'" + str(key) + "' : '" + str(info[key]) + "'<br/>"
        self.setToolTip(1, tip)

    def _set_game_map_icon(self, game):
        if game.featured_mod == "coop":  # no map icons for coop
            icon = util.THEME.icon("games/unknown_map.png")
        else:
            icon = fa.maps.preview(game.mapname)
            if not icon:
                dler = client.instance.map_downloader
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
        self.setTextAlignment(2, QtCore.Qt.AlignCenter)

    def _is_me(self, name):
        return client.instance.login == name

    def _is_friend(self, name):
        playerid = client.instance.players.getID(name)
        return client.instance.me.relations.model.is_friend(playerid)

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
        return GameUrl(GameUrlType.LIVE_REPLAY, game.mapname, game.featured_mod,
                       game.uid, name)

    def __lt__(self, other):
        return self.launch_time < other.launch_time

    def __le__(self, other):
        return self.launch_time <= other.launch_time

    def __gt__(self, other):
        return self.launch_time > other.launch_time

    def __ge__(self, other):
        return self.launch_time >= other.launch_time


class LiveReplaysWidgetHandler(object):
    def __init__(self, liveTree, client, gameset):
        self.liveTree = liveTree
        self.liveTree.itemDoubleClicked.connect(self.liveTreeDoubleClicked)
        self.liveTree.itemPressed.connect(self.liveTreePressed)
        self.liveTree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.liveTree.header().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.liveTree.header().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)

        self.client = client
        self.gameset = gameset
        self.gameset.newLiveGame.connect(self._newGame)
        self._addExistingGames(gameset)

        self.games = {}

    def liveTreePressed(self, item):
        if QtWidgets.QApplication.mouseButtons() != QtCore.Qt.RightButton:
            return

        if self.liveTree.indexOfTopLevelItem(item) != -1:
            item.setExpanded(True)
            return

        menu = QtWidgets.QMenu(self.liveTree)

        # Actions for Games and Replays
        actionReplay = QtWidgets.QAction("Replay in FA", menu)
        actionLink = QtWidgets.QAction("Copy Link", menu)

        # Adding to menu
        menu.addAction(actionReplay)
        menu.addAction(actionLink)

        # Triggers
        actionReplay.triggered.connect(lambda: self.liveTreeDoubleClicked(item))
        actionLink.triggered.connect(lambda: QtWidgets.QApplication.clipboard().setText(item.toolTip(0)))

        # Adding to menu
        menu.addAction(actionReplay)
        menu.addAction(actionLink)

        # Finally: Show the popup
        menu.popup(QtGui.QCursor.pos())

    def liveTreeDoubleClicked(self, item):
        """ This slot launches a live replay from eligible items in liveTree """

        if item.isDisabled():
            return

        if self.liveTree.indexOfTopLevelItem(item) == -1:
            # Notify other modules that we're watching a replay
            self.client.viewingReplay.emit(item.gurl)
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
        self.liveTree.takeTopLevelItem(self.liveTree.indexOfTopLevelItem(self.games[game]))
        del self.games[game]


class ReplayMetadata:
    def __init__(self, data):
        self.raw_data = data
        self.data = None
        self.is_broken = False
        self.is_incomplete = False

        try:
            self.data = json.loads(data)
        except json.decoder.JSONDecodeError:
            self.is_broken = True
            return

        self._validate_data()

    # FIXME - this is what the widget uses so far, we should define this
    # schema precisely in the future
    def _validate_data(self):
        if not isinstance(self.data, dict):
            self.is_broken = True
            return
        if not self.data.get('complete', False):
            self.is_incomplete = True
            return

        replay_schema = {
            "type": "object",
            "properties": {
                "num_players": {"type": "number"},
                "launched_at": {"type": "number"},
                "game_time": {
                    "type": "number",
                    "minimum": 0
                },
                "mapname": {"type": "string"},
                "title": {"type": "string"},
                "teams": {
                    "type": "object",
                    "patternProperties": {
                        ".*": {
                            "type": "array",
                            "items": {"type": "string"}
                            }
                        }
                    },
                "featured_mod": {"type": "string"}
                },
            "required": ["num_players", "mapname", "title", "teams",
                         "featured_mod"]
        }
        try:
            jsonschema.validate(self.data, replay_schema)
        except jsonschema.ValidationError:
            self.is_broken = True

    def launch_time(self):
        if 'launched_at' in self.data:
            return self.data['launched_at']
        elif 'game_time' in self.data:
            return self.data['game_time']
        else:
            return time.time()  # FIXME


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
        self.setForeground(1, QtGui.QColor("red"))   # FIXME: Needs to come from theme
        self.setText(2, "(replay parse error)")
        self.setForeground(2, QtGui.QColor("gray"))  # FIXME: Needs to come from theme

    def _setup_incomplete_appearance(self):
        self.setIcon(0, util.THEME.icon("replays/replay.png"))
        self.setText(1, self._replay_file)
        self.setText(2, "(replay doesn't have complete metadata)")
        self.setForeground(1, QtGui.QColor("yellow"))  # FIXME: Needs to come from theme

    def _setup_complete_appearance(self):
        data = self._metadata.data
        launch_time = time.localtime(self._metadata.launch_time())
        try:
            game_time = time.strftime("%H:%M", launch_time)
        except ValueError:
            game_time = "Unknown"

        icon = fa.maps.preview(data['mapname'])
        if icon:
            self.setIcon(0, icon)
        else:
            dler = client.instance.map_downloader
            dler.download_preview(data['mapname'], self._map_dl_request)
            self.setIcon(0, util.THEME.icon("games/unknown_map.png"))

        self.setToolTip(0, fa.maps.getDisplayName(data['mapname']))
        self.setText(0, game_time)
        self.setForeground(0, QtGui.QColor(client.instance.player_colors.get_color("default")))
        self.setText(1, data['title'])
        self.setToolTip(1, self._replay_file)

        playerlist = []
        for players in list(data['teams'].values()):
            playerlist.extend(players)
        self.setText(2, ", ".join(playerlist))
        self.setToolTip(2, ", ".join(playerlist))

        self.setText(3, data['featured_mod'])
        self.setTextAlignment(3, QtCore.Qt.AlignCenter)

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
        self.setText(3, "{} replays".format(len(children)))
        self.setForeground(3, QtGui.QColor(client.instance.player_colors.get_color("default")))

        for item in children:
            self.addChild(item)

    def _setup_broken_appearance(self):
        self.setForeground(0, QtGui.QColor("red"))  # FIXME: Needs to come from theme
        self.setText(1, "(not watchable)")
        self.setForeground(1, QtGui.QColor(client.instance.player_colors.get_color("default")))

    def _setup_incomplete_appearance(self):
        self.setForeground(0, QtGui.QColor("yellow"))  # FIXME: Needs to come from theme
        self.setText(1, "(watchable)")
        self.setForeground(1, QtGui.QColor(client.instance.player_colors.get_color("default")))

    def _setup_legacy_appearance(self):
        self.setForeground(0, QtGui.QColor(client.instance.player_colors.get_color("default")))
        self.setForeground(1, QtGui.QColor(client.instance.player_colors.get_color("default")))
        self.setText(1, "(old replay system)")

    def _setup_date_appearance(self):
        self.setForeground(0, QtGui.QColor(client.instance.player_colors.get_color("player")))


class LocalReplaysWidgetHandler(object):
    def __init__(self, myTree):
        self.myTree = myTree
        self.myTree.itemDoubleClicked.connect(self.myTreeDoubleClicked)
        self.myTree.itemPressed.connect(self.myTreePressed)
        self.myTree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.myTree.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.myTree.header().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.myTree.header().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        self.myTree.modification_time = 0

        replay_cache = os.path.join(util.CACHE_DIR, "local_replays_metadata")
        self.replay_files = LocalReplayMetadataCache(util.REPLAY_DIR,
                                                     replay_cache)

    def myTreePressed(self, item):
        if QtWidgets.QApplication.mouseButtons() != QtCore.Qt.RightButton:
            return

        if item.isDisabled():
            return

        if self.myTree.indexOfTopLevelItem(item) != -1:
            return

        menu = QtWidgets.QMenu(self.myTree)

        # Actions for Games and Replays
        actionReplay = QtWidgets.QAction("Replay", menu)
        actionExplorer = QtWidgets.QAction("Show in Explorer", menu)

        # Adding to menu
        menu.addAction(actionReplay)
        menu.addAction(actionExplorer)

        # Triggers
        actionReplay.triggered.connect(lambda: self.myTreeDoubleClicked(item))
        actionExplorer.triggered.connect(lambda: util.showFileInFileBrowser(item.replay_path()))

        # Adding to menu
        menu.addAction(actionReplay)
        menu.addAction(actionExplorer)

        # Finally: Show the popup
        menu.popup(QtGui.QCursor.pos())

    def myTreeDoubleClicked(self, item):
        if item.isDisabled():
            return

        if self.myTree.indexOfTopLevelItem(item) == -1:
            replay(item.replay_path())

    def updatemyTree(self):
        modification_time = os.path.getmtime(util.REPLAY_DIR)
        if self.myTree.modification_time == modification_time:  # anything changed?
            return  # nothing changed -> don't redo
        self.myTree.modification_time = modification_time
        self.myTree.clear()

        # We put the replays into buckets by day first, then we add them to the treewidget.
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
        # Now, create a top level treeWidgetItem for every bucket, and put the bucket's contents into them
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
            with open(self._cache_file, "rt") as fh:
                for line in fh:
                    filename, metadata = line.split(':', 1)
                    self._cache[filename] = ReplayMetadata(metadata)
        self.cache_loaded = True

    def save_cache(self):
        if not self._cache_differs_much_from_files():
            return
        with open(self._cache_file, "wt") as fh:
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
                with open(target_file, "rt") as fh:
                    metadata = fh.readline()
                    self._cache[filename] = ReplayMetadata(metadata)
                self._new_cache_entries.add(filename)
            except IOError:
                raise KeyError

        self._used_cache_entries.add(filename)
        return self._cache[filename]


class ReplayVaultWidgetHandler(object):
    HOST = "lobby.faforever.com"
    PORT = 11002

    # connect to save/restore persistence settings for checkboxes & search parameters
    automatic = Settings.persisted_property("replay/automatic", default_value=False, type=bool)
    spoiler_free = Settings.persisted_property("replay/spoilerFree", default_value=True, type=bool)

    def __init__(self, widget, dispatcher, client, gameset, playerset):
        self._w = widget
        self._dispatcher = dispatcher
        self.client = client
        self._gameset = gameset
        self._playerset = playerset

        self.onlineReplays = {}
        self.selectedReplay = None
        self.vault_connection = ReplaysConnection(self._dispatcher, self.HOST, self.PORT)
        self.client.lobby_info.replayVault.connect(self.replayVault)
        self.replayDownload = QNetworkAccessManager()
        self.replayDownload.finished.connect(self.finishRequest)

        self.searching = False
        self.searchInfo = "<font color='gold'><b>Searching...</b></font>"

        _w = self._w
        _w.onlineTree.setItemDelegate(ReplayItemDelegate(_w))
        _w.onlineTree.itemDoubleClicked.connect(self.onlineTreeDoubleClicked)
        _w.onlineTree.itemPressed.connect(self.onlineTreeClicked)

        _w.searchButton.pressed.connect(self.searchVault)
        _w.playerName.returnPressed.connect(self.searchVault)
        _w.mapName.returnPressed.connect(self.searchVault)
        _w.automaticCheckbox.stateChanged.connect(self.automaticCheckboxchange)
        _w.spoilerCheckbox.stateChanged.connect(self.spoilerCheckboxchange)
        _w.RefreshResetButton.pressed.connect(self.resetRefreshPressed)

        # restore persistent checkbox settings
        _w.automaticCheckbox.setChecked(self.automatic)
        _w.spoilerCheckbox.setChecked(self.spoiler_free)

    def searchVault(self, minRating=None, mapName=None, playerName=None, modListIndex=None):
        w = self._w
        if minRating is not None:
            w.minRating.setValue(minRating)
        if mapName is not None:
            w.mapName.setText(mapName)
        if playerName is not None:
            w.playerName.setText(playerName)
        if modListIndex is not None:
            w.modList.setCurrentIndex(modListIndex)

        # Map Search helper - the secondary server has a problem with blanks (fix until change to api)
        map_name = w.mapName.text().replace(" ", "*")

        """ search for some replays """
        self._w.searchInfoLabel.setText(self.searchInfo)
        self.searching = True
        self.vault_connection.connect_()
        self.vault_connection.send(dict(command="search",
                                        rating=w.minRating.value(),
                                        map=map_name,
                                        player=w.playerName.text(),
                                        mod=w.modList.currentText()))
        self._w.onlineTree.clear()

    def reloadView(self):
        if not self.searching:  # something else is already in the pipe from SearchVault
            if self.automatic or self.onlineReplays == {}:  # refresh on Tab change or only the first time
                self._w.searchInfoLabel.setText(self.searchInfo)
                self.vault_connection.connect_()
                self.vault_connection.send(dict(command="list"))

    def onlineTreeClicked(self, item):
        if QtWidgets.QApplication.mouseButtons() == QtCore.Qt.RightButton:
            if type(item.parent) == ReplaysWidget:      # FIXME - hack
                item.pressed(item)
        else:
            self.selectedReplay = item
            if hasattr(item, "moreInfo"):
                if item.moreInfo is False:
                    self.vault_connection.connect_()
                    self.vault_connection.send(dict(command="info_replay", uid=item.uid))
                elif item.spoiled != self._w.spoilerCheckbox.isChecked():
                    self._w.replayInfos.clear()
                    self._w.replayInfos.setHtml(item.replayInfo)
                    item.resize()
                else:
                    self._w.replayInfos.clear()
                    item.generateInfoPlayersHtml()

    def onlineTreeDoubleClicked(self, item):
        if hasattr(item, "duration"):  # it's a game not a date separator
            if "playing" in item.duration:  # live game will not be in vault
                # search result isn't updated automatically - so game status might have changed
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
                        wait_str = time.strftime('%M Min %S Sec', time.gmtime(game.LIVE_REPLAY_DELAY_SECS -
                                                                              (time.time() - game.launched_at)))
                        QtWidgets.QMessageBox.information(client.instance, "5 Minute Live Game Delay",
                                                          "It is too early to join the Game.\n"
                                                          "You have to wait " + wait_str + " to join.")
                else:  # game ended - ask to start replay
                    if QtWidgets.QMessageBox.question(client.instance, "Live Game ended",
                                                      "Would you like to watch the replay from the vault?",
                                                      QtWidgets.QMessageBox.Yes,
                                                      QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
                        self.replayDownload.get(QNetworkRequest(QtCore.QUrl(item.url)))

            else:  # start replay
                if hasattr(item, "url"):
                    self.replayDownload.get(QNetworkRequest(QtCore.QUrl(item.url)))

    def _startReplay(self, name):
        if name is None or name not in self._playerset:
            return
        player = self._playerset[name]

        if not player.currentGame:
            return
        replay(player.currentGame.url(player.id))

    def automaticCheckboxchange(self, state):
        self.automatic = state

    def spoilerCheckboxchange(self, state):
        self.spoiler_free = state
        if self.selectedReplay:  # if something is selected in the tree to the left
            if type(self.selectedReplay) == ReplayItem:  # and if it is a game
                self.selectedReplay.generateInfoPlayersHtml()  # then we redo it

    def resetRefreshPressed(self):  # reset search parameter and reload recent Replays List
        self._w.searchInfoLabel.setText(self.searchInfo)
        self.vault_connection.connect_()
        self.vault_connection.send(dict(command="list"))
        self._w.minRating.setValue(0)
        self._w.mapName.setText("")
        self._w.playerName.setText("")
        self._w.modList.setCurrentIndex(0)  # "All"

    def finishRequest(self, reply):
        if reply.error() != QNetworkReply.NoError:
            QtWidgets.QMessageBox.warning(self._w, "Network Error", reply.errorString())
        else:
            faf_replay = QtCore.QFile(os.path.join(util.CACHE_DIR, "temp.fafreplay"))
            faf_replay.open(QtCore.QIODevice.WriteOnly | QtCore.QIODevice.Truncate)
            faf_replay.write(reply.readAll())
            faf_replay.flush()
            faf_replay.close()
            replay(os.path.join(util.CACHE_DIR, "temp.fafreplay"))

    def replayVault(self, message):
        action = message["action"]
        self._w.searchInfoLabel.clear()
        if action == "list_recents":
            self.onlineReplays = {}
            replays = message["replays"]
            for replay in replays:
                uid = replay["id"]

                if uid not in self.onlineReplays:
                    self.onlineReplays[uid] = ReplayItem(uid, self._w)
                    self.onlineReplays[uid].update(replay, self.client)
                else:
                    self.onlineReplays[uid].update(replay, self.client)

            self.updateOnlineTree()
            self._w.replayInfos.clear()
            self._w.RefreshResetButton.setText("Refresh Recent List")

        elif action == "info_replay":
            uid = message["uid"]
            if uid in self.onlineReplays:
                self.onlineReplays[uid].infoPlayers(message["players"])

        elif action == "search_result":
            self.searching = False
            self.onlineReplays = {}
            replays = message["replays"]
            for replay in replays:
                uid = replay["id"]

                if uid not in self.onlineReplays:
                    self.onlineReplays[uid] = ReplayItem(uid, self._w)
                    self.onlineReplays[uid].update(replay, self.client)
                else:
                    self.onlineReplays[uid].update(replay, self.client)

            self.updateOnlineTree()
            self._w.replayInfos.clear()
            self._w.RefreshResetButton.setText("Reset Search to Recent")

    def updateOnlineTree(self):
        self.selectedReplay = None  # clear because won't be part of the new tree
        self._w.replayInfos.clear()
        self._w.onlineTree.clear()
        buckets = {}
        for uid in self.onlineReplays:
            bucket = buckets.setdefault(self.onlineReplays[uid].startDate, [])
            bucket.append(self.onlineReplays[uid])

        for bucket in buckets.keys():
            bucket_item = QtWidgets.QTreeWidgetItem()
            self._w.onlineTree.addTopLevelItem(bucket_item)

            bucket_item.setIcon(0, util.THEME.icon("replays/bucket.png"))
            bucket_item.setText(0, "<font color='white'>" + bucket+"</font>")
            bucket_item.setText(1, "<font color='white'>" + str(len(buckets[bucket])) + " replays</font>")

            for replay in buckets[bucket]:
                bucket_item.addChild(replay)
                replay.setFirstColumnSpanned(True)
                replay.setIcon(0, replay.icon)

            bucket_item.setExpanded(True)


class ReplaysWidget(BaseClass, FormClass):
    def __init__(self, client, dispatcher, gameset, playerset):
        super(BaseClass, self).__init__()

        self.setupUi(self)

        self.liveManager = LiveReplaysWidgetHandler(self.liveTree, client, gameset)
        self.localManager = LocalReplaysWidgetHandler(self.myTree)
        self.vaultManager = ReplayVaultWidgetHandler(self, dispatcher, client, gameset, playerset)

        logger.info("Replays Widget instantiated.")

    def set_player(self, name):
        self.setCurrentIndex(2)  # focus on Online Fault
        self.vaultManager.searchVault(-1400, "", name, 0)

    def focusEvent(self, event):
        self.localManager.updatemyTree()
        self.vaultManager.reloadView()
        return BaseClass.focusEvent(self, event)

    def showEvent(self, event):
        self.localManager.updatemyTree()
        self.vaultManager.reloadView()
        return BaseClass.showEvent(self, event)
