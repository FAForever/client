from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from fa.replay import replay
from config import Settings
import util
import os
import fa
import time
import client
import json

import logging
logger = logging.getLogger(__name__)

LIVEREPLAY_DELAY = 5  # livereplay delay in minutes
LIVEREPLAY_DELAY_TIME = LIVEREPLAY_DELAY * 60  # livereplay delay for time() (in seconds)
LIVEREPLAY_DELAY_QTIMER = LIVEREPLAY_DELAY * 60000  # livereplay delay for Qtimer (in milliseconds)

from replays.replayitem import ReplayItem, ReplayItemDelegate
from model.game import GameState
from replays.connection import ReplaysConnection

# Replays uses the new Inheritance Based UI creation pattern
# This allows us to do all sorts of awesome stuff by overriding methods etc.

FormClass, BaseClass = util.THEME.loadUiType("replays/replays.ui")


class LiveReplayItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, time):
        QtWidgets.QTreeWidgetItem.__init__(self)
        self.time = time

    def __lt__(self, other):
        return self.time < other.time

    def __le__(self, other):
        return self.time <= other.time

    def __gt__(self, other):
        return self.time > other.time

    def __ge__(self, other):
        return self.time >= other.time


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
            self.client.viewingReplay.emit(item.url)
            replay(item.url)

    def _addExistingGames(self, gameset):
        for game in gameset:
            if game.state == GameState.PLAYING:
                self._newGame(game)

    def _newGame(self, game):
        launched_at = game.launched_at if game.launched_at is not None else time.time()

        item = LiveReplayItem(launched_at)
        self.liveTree.insertTopLevelItem(0, item)

        if time.time() - launched_at < LIVEREPLAY_DELAY_TIME:
            item.setHidden(True)
            # The delay is there because we have a delay in the livereplay server
            # To get the delay right on client start, subtract the already passed game time
            delay_time = LIVEREPLAY_DELAY_QTIMER - int(1000*(time.time() - launched_at))
            QtCore.QTimer.singleShot(delay_time, lambda: item.setHidden(False))

        self.games[game] = (item, launched_at)
        game.gameUpdated.connect(self._updateGame)
        game.gameClosed.connect(self._removeGame)
        self._updateGame(game)

    def _updateGame(self, game):
        item, launched_at = self.games[game]
        item.takeChildren()  # Clear the children of this item before we're updating it

        # For debugging purposes, format our tooltip for the top level items
        # so it contains a human-readable representation of the info dictionary
        info = game.to_dict()
        tip = ""
        for key in list(info.keys()):
            tip += "'" + str(key) + "' : '" + str(info[key]) + "'<br/>"

        item.setToolTip(1, tip)

        icon = fa.maps.preview(game.mapname)
        item.setToolTip(0, fa.maps.getDisplayName(game.mapname))
        if not icon:
            self.client.downloader.downloadMap(game.mapname, item, True)
            icon = util.THEME.icon("games/unknown_map.png")

        item.setText(0, time.strftime("%Y-%m-%d  -  %H:%M", time.localtime(launched_at)))
        item.setForeground(0, QtGui.QColor(client.instance.getColor("default")))

        if game.featured_mod == "coop":  # no map icons for coop
            item.setIcon(0, util.THEME.icon("games/unknown_map.png"))
        else:
            item.setIcon(0, icon)
        if game.featured_mod == "ladder1v1":
            item.setText(1, game.title)
        else:
            item.setText(1, game.title + "    -    [host: " + game.host + "]")
        item.setForeground(1, QtGui.QColor(client.instance.getColor("player")))

        item.setText(2, game.featured_mod)
        item.setTextAlignment(2, QtCore.Qt.AlignCenter)

        if not game.teams:
            item.setDisabled(True)

        # This game is the game the player is currently in
        mygame = False

        # Create player entries for all the live players in a match
        for team in game.teams:
            if team == "-1":  # skip observers, they don't seem to stream livereplays
                continue

            for name in game.teams[team]:
                playeritem = QtWidgets.QTreeWidgetItem()
                playeritem.setText(0, name)

                playerid = self.client.players.getID(name)

                url = QtCore.QUrl()
                url.setScheme("faflive")
                url.setHost("lobby.faforever.com")
                url.setPath("/" + str(game.uid) + "/" + name + ".SCFAreplay")
                query = QtCore.QUrlQuery()
                query.addQueryItem("map", game.mapname)
                query.addQueryItem("mod", game.featured_mod)
                url.setQuery(query)

                playeritem.url = url
                if client.instance.login == name:
                    mygame = True
                    item.setForeground(1, QtGui.QColor(client.instance.getColor("self")))
                    playeritem.setForeground(0, QtGui.QColor(client.instance.getColor("self")))
                    playeritem.setToolTip(0, url.toString())
                    playeritem.setIcon(0, util.THEME.icon("replays/replay.png"))

                elif client.instance.me.isFriend(playerid):
                    if not mygame:
                        item.setForeground(1, QtGui.QColor(client.instance.getColor("friend")))
                    playeritem.setForeground(0, QtGui.QColor(client.instance.getColor("friend")))
                    playeritem.setToolTip(0, url.toString())
                    playeritem.setIcon(0, util.THEME.icon("replays/replay.png"))

                elif client.instance.players.isPlayer(playerid):
                    playeritem.setForeground(0, QtGui.QColor(client.instance.getColor("player")))
                    playeritem.setToolTip(0, url.toString())
                    playeritem.setIcon(0, util.THEME.icon("replays/replay.png"))

                else:
                    playeritem.setForeground(0, QtGui.QColor(client.instance.getColor("default")))
                    playeritem.setDisabled(True)

                item.addChild(playeritem)

    def _removeGame(self, game):
        self.liveTree.takeTopLevelItem(self.liveTree.indexOfTopLevelItem(self.games[game][0]))
        del self.games[game]

    def displayReplay(self):
        for uid in self.games:
            item = self.games[uid]
            if time.time() - item.info.get('launched_at', time.time()) > LIVEREPLAY_DELAY_TIME and item.isHidden():
                item.setHidden(False)


class LocalReplaysWidgetHandler(object):
    def __init__(self, myTree):
        self.myTree = myTree
        self.myTree.itemDoubleClicked.connect(self.myTreeDoubleClicked)
        self.myTree.itemPressed.connect(self.myTreePressed)
        self.myTree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.myTree.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.myTree.header().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.myTree.header().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)

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
        actionExplorer.triggered.connect(lambda: util.showFileInFileBrowser(item.filename))

        # Adding to menu
        menu.addAction(actionReplay)
        menu.addAction(actionExplorer)

        # Finally: Show the popup
        menu.popup(QtGui.QCursor.pos())

    def myTreeDoubleClicked(self, item):
        if item.isDisabled():
            return

        if self.myTree.indexOfTopLevelItem(item) == -1:
            replay(item.filename)

    def updatemyTree(self):
        self.myTree.clear()

        # We put the replays into buckets by day first, then we add them to the treewidget.
        buckets = {}

        cache = self.loadLocalCache()
        cache_add = {}
        cache_hit = {}
        # Iterate
        for infile in os.listdir(util.REPLAY_DIR):
            if infile.endswith(".scfareplay"):
                bucket = buckets.setdefault("legacy", [])

                item = QtWidgets.QTreeWidgetItem()
                item.setText(1, infile)
                item.filename = os.path.join(util.REPLAY_DIR, infile)
                item.setIcon(0, util.THEME.icon("replays/replay.png"))
                item.setForeground(0, QtGui.QColor(client.instance.getColor("default")))

                bucket.append(item)

            elif infile.endswith(".fafreplay"):
                item = QtWidgets.QTreeWidgetItem()
                try:
                    item.filename = os.path.join(util.REPLAY_DIR, infile)
                    basename = os.path.basename(item.filename)
                    if basename in cache:
                        oneline = cache[basename]
                        cache_hit[basename] = oneline
                    else:
                        with open(item.filename, "rt") as fh:
                            oneline = fh.readline()
                            cache_add[basename] = oneline

                    item.info = json.loads(oneline)

                    # Parse replayinfo into data
                    if item.info.get('complete', False):
                        t = time.localtime(item.info.get('launched_at', item.info.get('game_time', time.time())))
                        game_date = time.strftime("%Y-%m-%d", t)
                        game_hour = time.strftime("%H:%M", t)

                        bucket = buckets.setdefault(game_date, [])

                        icon = fa.maps.preview(item.info['mapname'])
                        if icon:
                            item.setIcon(0, icon)
                        else:
                            client.instance.downloader.downloadMap(item.info['mapname'], item, True)
                            item.setIcon(0, util.THEME.icon("games/unknown_map.png"))
                        item.setToolTip(0, fa.maps.getDisplayName(item.info['mapname']))
                        item.setText(0, game_hour)
                        item.setForeground(0, QtGui.QColor(client.instance.getColor("default")))

                        item.setText(1, item.info['title'])
                        item.setToolTip(1, infile)

                        # Hacky way to quickly assemble a list of all the players, but including the observers
                        playerlist = []
                        for _, players in list(item.info['teams'].items()):
                            playerlist.extend(players)
                        item.setText(2, ", ".join(playerlist))
                        item.setToolTip(2, ", ".join(playerlist))

                        # Add additional info
                        item.setText(3, item.info['featured_mod'])
                        item.setTextAlignment(3, QtCore.Qt.AlignCenter)
                        item.setForeground(1, QtGui.QColor(client.instance.players.getUserColor(item.info.get('recorder', ""))))
                    else:
                        bucket = buckets.setdefault("incomplete", [])
                        item.setIcon(0, util.THEME.icon("replays/replay.png"))
                        item.setText(1, infile)
                        item.setText(2, "(replay doesn't have complete metadata)")
                        item.setForeground(1, QtGui.QColor("yellow"))  # FIXME: Needs to come from theme

                except Exception as ex:
                    bucket = buckets.setdefault("broken", [])
                    item.setIcon(0, util.THEME.icon("replays/broken.png"))
                    item.setText(1, infile)
                    item.setForeground(1, QtGui.QColor("red"))   # FIXME: Needs to come from theme
                    item.setText(2, "(replay parse error)")
                    item.setForeground(2, QtGui.QColor("gray"))  # FIXME: Needs to come from theme
                    logger.exception("Exception parsing replay {}: {}".format(infile, ex))

                bucket.append(item)

        if len(cache_add) > 10 or len(cache) - len(cache_hit) > 10:
            self.saveLocalCache(cache_hit, cache_add)
        # Now, create a top level treewidgetitem for every bucket, and put the bucket's contents into them
        for bucket in buckets.keys():
            bucket_item = QtWidgets.QTreeWidgetItem()

            if bucket == "broken":
                bucket_item.setForeground(0, QtGui.QColor("red"))  # FIXME: Needs to come from theme
                bucket_item.setText(1, "(not watchable)")
                bucket_item.setForeground(1, QtGui.QColor(client.instance.getColor("default")))
            elif bucket == "incomplete":
                bucket_item.setForeground(0, QtGui.QColor("yellow"))  # FIXME: Needs to come from theme
                bucket_item.setText(1, "(watchable)")
                bucket_item.setForeground(1, QtGui.QColor(client.instance.getColor("default")))
            elif bucket == "legacy":
                bucket_item.setForeground(0, QtGui.QColor(client.instance.getColor("default")))
                bucket_item.setForeground(1, QtGui.QColor(client.instance.getColor("default")))
                bucket_item.setText(1, "(old replay system)")
            else:
                bucket_item.setForeground(0, QtGui.QColor(client.instance.getColor("player")))

            bucket_item.setIcon(0, util.THEME.icon("replays/bucket.png"))
            bucket_item.setText(0, bucket)
            bucket_item.setText(3, str(len(buckets[bucket])) + " replays")
            bucket_item.setForeground(3, QtGui.QColor(client.instance.getColor("default")))

            self.myTree.addTopLevelItem(bucket_item)
            #self.myTree.setFirstItemColumnSpanned(bucket_item, True)

            for replay in buckets[bucket]:
                bucket_item.addChild(replay)

    def loadLocalCache(self):
        cache_fname = os.path.join(util.CACHE_DIR, "local_replays_metadata")
        cache = {}
        if os.path.exists(cache_fname):
            with open(cache_fname, "rt") as fh:
                for line in fh:
                    filename, metadata = line.split(':', 1)
                    cache[filename] = metadata
        return cache

    def saveLocalCache(self, cache_hit, cache_add):
        with open(os.path.join(util.CACHE_DIR, "local_replays_metadata"), "wt") as fh:
            for filename, metadata in cache_hit.items():
                fh.write(filename + ":" + metadata)
            for filename, metadata in cache_add.items():
                fh.write(filename + ":" + metadata)


class ReplayVaultWidgetHandler(object):
    HOST = "lobby.faforever.com"
    PORT = 11002

    # connect to save/restore persistence settings for checkboxes & search parameters
    automatic = Settings.persisted_property("replay/automatic", default_value=False, type=bool)
    spoiler_free = Settings.persisted_property("replay/spoilerFree", default_value=True, type=bool)

    def __init__(self, widget, dispatcher, client):
        self._w = widget
        self._dispatcher = dispatcher
        self.client = client

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

    def searchVault(self, minRating=None, mapName=None,
                    playerName=None, modListIndex=None):
        w = self._w
        if minRating:
            w.minRating.setValue(minRating)
        if mapName:
            w.mapName.setText(mapName)
        if playerName:
            w.playerName.setText(playerName)
        if modListIndex:
            w.modList.setCurrentIndex(modListIndex)

        """ search for some replays """
        self._w.searchInfoLabel.setText(self.searchInfo)
        self.searching = True
        self.vault_connection.connect()
        self.vault_connection.send(dict(command="search",
                                        rating=w.minRating.value(),
                                        map=w.mapName.text(),
                                        player=w.playerName.text(),
                                        mod=w.modList.currentText()))
        self._w.onlineTree.clear()

    def reloadView(self):
        if not self.searching:  # something else is already in the pipe from SearchVault
            if self.automatic or self.onlineReplays == {}:  # refresh on Tab change or only the first time
                self._w.searchInfoLabel.setText(self.searchInfo)
                self.vault_connection.connect()
                self.vault_connection.send(dict(command="list"))

    def onlineTreeClicked(self, item):
        if QtWidgets.QApplication.mouseButtons() == QtCore.Qt.RightButton:
            if type(item.parent) == ReplaysWidget:      # FIXME - hack
                item.pressed(item)
        else:
            self.selectedReplay = item
            if hasattr(item, "moreInfo"):
                if item.moreInfo is False:
                    self.vault_connection.connect()
                    self.vault_connection.send(dict(command="info_replay", uid=item.uid))
                elif item.spoiled != self._w.spoilerCheckbox.isChecked():
                    self._w.replayInfos.clear()
                    self._w.replayInfos.setHtml(item.replayInfo)
                    item.resize()
                else:
                    self._w.replayInfos.clear()
                    item.generateInfoPlayersHtml()

    def onlineTreeDoubleClicked(self, item):
        if hasattr(item, "duration"):
            if "playing" in item.duration:  # live game will not be in vault
                if not item.live_delay:  # live game under 5min
                    if item.mod == "ladder1v1":
                        name = item.name[:item.name.find(" ")]  # "name vs name"
                    else:
                        for team in item.teams:  # find a player...
                            for player in item.teams[team]:
                                name = player["name"]
                                if name != "":
                                    break
                            if name != "":
                                break
                    if name in client.instance.urls:  # join live game
                        replay(client.instance.urls[name])
            else:  # start replay
                if hasattr(item, "url"):
                    self.replayDownload.get(QNetworkRequest(QtCore.QUrl(item.url)))

    def automaticCheckboxchange(self, state):
        self.automatic = state

    def spoilerCheckboxchange(self, state):
        self.spoiler_free = state
        if self.selectedReplay:  # if something is selected in the tree to the left
            if type(self.selectedReplay) == ReplayItem:  # and if it is a game
                self.selectedReplay.generateInfoPlayersHtml()  # then we redo it

    def resetRefreshPressed(self):  # reset search parameter and reload recent Replays List
        self._w.searchInfoLabel.setText(self.searchInfo)
        self.vault_connection.connect()
        self.vault_connection.send(dict(command="list"))
        self._w.minRating.setValue(0)
        self._w.mapName.setText("")
        self._w.playerName.setText("")
        self._w.modList.setCurrentIndex(0)  # "All"

    def finishRequest(self, reply):
        if reply.error() != QNetworkReply.NoError:
            QtWidgets.QMessageBox.warning(self, "Network Error", reply.errorString())
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
    def __init__(self, client, dispatcher, gameset):
        super(BaseClass, self).__init__()

        self.setupUi(self)

        # self.replayVault.setVisible(False)
        self.client = client

        self.liveManager = LiveReplaysWidgetHandler(self.liveTree, self.client, gameset)
        self.localManager = LocalReplaysWidgetHandler(self.myTree)
        self.vaultManager = ReplayVaultWidgetHandler(self, dispatcher, client)

        logger.info("Replays Widget instantiated.")

    def focusEvent(self, event):
        self.localManager.updatemyTree()
        self.vaultManager.reloadView()
        return BaseClass.focusEvent(self, event)

    def showEvent(self, event):
        self.localManager.updatemyTree()
        self.vaultManager.reloadView()
        return BaseClass.showEvent(self, event)
