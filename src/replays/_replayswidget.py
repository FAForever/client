from PyQt5 import QtCore, QtWidgets, QtNetwork, QtGui
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

# Replays uses the new Inheritance Based UI creation pattern
# This allows us to do all sorts of awesome stuff by overriding methods etc.

FormClass, BaseClass = util.loadUiType("replays/replays.ui")

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


class ReplaysWidget(BaseClass, FormClass):
    SOCKET = 11002
    HOST   = "lobby.faforever.com"

    # connect to save/restore persistence settings for checkboxes & search parameters
    automatic = Settings.persisted_property("replay/automatic", default_value=False, type=bool)
    spoiler_free = Settings.persisted_property("replay/spoilerFree", default_value=True, type=bool)

    def __init__(self, client, dispatcher):
        super(BaseClass, self).__init__()

        self.setupUi(self)

        # self.replayVault.setVisible(False)
        self.client = client
        self._dispatcher = dispatcher
        client.replaysTab.layout().addWidget(self)
        
        client.lobby_info.gameInfo.connect(self.processGameInfo)
        client.lobby_info.replayVault.connect(self.replayVault)
        
        self.onlineReplays = {}
        self.onlineTree.setItemDelegate(ReplayItemDelegate(self))
        self.replayDownload = QNetworkAccessManager()
        self.replayDownload.finished.connect(self.finishRequest)
        
        # sending request to replay vault
        self.searchButton.pressed.connect(self.searchVault)
        self.playerName.returnPressed.connect(self.searchVault)
        self.mapName.returnPressed.connect(self.searchVault)
        self.automaticCheckbox.stateChanged.connect(self.automaticCheckboxchange)
        self.spoilerCheckbox.stateChanged.connect(self.spoilerCheckboxchange)
        self.RefreshResetButton.pressed.connect(self.ResetRefreshpressed)

        self.myTree.itemDoubleClicked.connect(self.myTreeDoubleClicked)
        self.myTree.itemPressed.connect(self.myTreePressed)
        self.myTree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.myTree.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.myTree.header().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.myTree.header().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        
        self.liveTree.itemDoubleClicked.connect(self.liveTreeDoubleClicked)
        self.liveTree.itemPressed.connect(self.liveTreePressed)
        self.liveTree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.liveTree.header().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.liveTree.header().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        
        self.games = {}

        self.onlineTree.itemDoubleClicked.connect(self.onlineTreeDoubleClicked)
        self.onlineTree.itemPressed.connect(self.onlineTreeClicked)
        self.selectedReplay = None

        # replay vault connection to server
        self.searching = False
        self.searchInfo = "<font color='gold'><b>Searching...</b></font>"
        self.blockSize = 0
        self.replayVaultSocket = QtNetwork.QTcpSocket()
        self.replayVaultSocket.error.connect(self.handleServerError)
        self.replayVaultSocket.readyRead.connect(self.readDataFromServer)
        self.replayVaultSocket.disconnected.connect(self.disconnected)
        self.replayVaultSocket.error.connect(self.errored) 

        # restore persistent checkbox settings
        self.automaticCheckbox.setChecked(self.automatic)
        self.spoilerCheckbox.setChecked(self.spoiler_free)

        logger.info("Replays Widget instantiated.")

    def searchVault(self):
        """ search for some replays """
        self.searchInfoLabel.setText(self.searchInfo)
        self.searching = True
        self.connectToReplayVault()
        self.send(dict(command="search", rating=self.minRating.value(), map=self.mapName.text(),
                                player=self.playerName.text(), mod=self.modList.currentText()))
        self.onlineTree.clear()

    def reloadView(self):
        if not self.searching:  # something else is already in the pipe from SearchVault
            if self.automatic or self.onlineReplays == {}:  # refresh on Tap change or only the first time
                self.searchInfoLabel.setText(self.searchInfo)
                self.connectToReplayVault()
                self.send(dict(command="list"))

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

    def onlineTreeClicked(self, item):
        if QtWidgets.QApplication.mouseButtons() == QtCore.Qt.RightButton:
            if type(item.parent) == ReplaysWidget:
                item.pressed(item)
        else:
            self.selectedReplay = item
            if hasattr(item, "moreInfo"):
                if item.moreInfo is False:
                    self.connectToReplayVault()
                    self.send(dict(command="info_replay", uid=item.uid))
                elif item.spoiled != self.spoilerCheckbox.isChecked():
                    self.replayInfos.clear()
                    self.replayInfos.setHtml(item.replayInfo)
                    item.resize()
                else:
                    self.replayInfos.clear()
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
        self.automatic = state  # save state .. no magic

    def spoilerCheckboxchange(self, state):
        self.spoiler_free = state  # save state .. no magic
        if self.selectedReplay:  # if something is selected in the tree to the left
            if type(self.selectedReplay) == ReplayItem:  # and if it is a game
                self.selectedReplay.generateInfoPlayersHtml()  # then we redo it

    def ResetRefreshpressed(self):  # reset search parameter and reload recent Replays List
        self.searchInfoLabel.setText(self.searchInfo)
        self.connectToReplayVault()
        self.send(dict(command="list"))
        self.minRating.setValue(0)
        self.mapName.setText("")
        self.playerName.setText("")
        self.modList.setCurrentIndex(0)  # "All"

    def replayVault(self, message):
        action = message["action"]
        self.searchInfoLabel.clear()
        if action == "list_recents":
            self.onlineReplays = {}
            replays = message["replays"]
            for replay in replays:
                uid = replay["id"]
        
                if uid not in self.onlineReplays:
                    self.onlineReplays[uid] = ReplayItem(uid, self)
                    self.onlineReplays[uid].update(replay, self.client)
                else:
                    self.onlineReplays[uid].update(replay, self.client)
                    
            self.updateOnlineTree()
            self.replayInfos.clear()
            self.RefreshResetButton.setText("Refresh Recent List")

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
                    self.onlineReplays[uid] = ReplayItem(uid, self)
                    self.onlineReplays[uid].update(replay, self.client)
                else:
                    self.onlineReplays[uid].update(replay, self.client)
                    
            self.updateOnlineTree()
            self.replayInfos.clear()
            self.RefreshResetButton.setText("Reset Search to Recent")

    def focusEvent(self, event):
        self.updatemyTree()
        self.reloadView()
        return BaseClass.focusEvent(self, event)
    
    def showEvent(self, event):
        self.updatemyTree()
        self.reloadView()
        return BaseClass.showEvent(self, event)

    def updateOnlineTree(self):
        self.selectedReplay = None  # clear because won't be part of the new tree
        self.replayInfos.clear()
        self.onlineTree.clear()
        buckets = {}
        for uid in self.onlineReplays:
            bucket = buckets.setdefault(self.onlineReplays[uid].startDate, [])
            bucket.append(self.onlineReplays[uid])

        for bucket in buckets.keys():
            bucket_item = QtWidgets.QTreeWidgetItem()
            self.onlineTree.addTopLevelItem(bucket_item)
            
            bucket_item.setIcon(0, util.icon("replays/bucket.png"))                                
            bucket_item.setText(0, "<font color='white'>" + bucket+"</font>")
            bucket_item.setText(1, "<font color='white'>" + str(len(buckets[bucket])) + " replays</font>")

            for replay in buckets[bucket]:
                bucket_item.addChild(replay)
                replay.setFirstColumnSpanned(True)
                replay.setIcon(0, replay.icon)
                
            bucket_item.setExpanded(True)
    
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
                item.setIcon(0, util.icon("replays/replay.png"))
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
                            self.client.downloader.downloadMap(item.info['mapname'], item, True)
                            item.setIcon(0, util.icon("games/unknown_map.png"))
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
                        item.setIcon(0, util.icon("replays/replay.png"))
                        item.setText(1, infile)
                        item.setText(2, "(replay doesn't have complete metadata)")
                        item.setForeground(1, QtGui.QColor("yellow"))  # FIXME: Needs to come from theme

                except Exception as ex:
                    bucket = buckets.setdefault("broken", [])                    
                    item.setIcon(0, util.icon("replays/broken.png"))
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
                
            bucket_item.setIcon(0, util.icon("replays/bucket.png"))                                
            bucket_item.setText(0, bucket)
            bucket_item.setText(3, str(len(buckets[bucket])) + " replays")
            bucket_item.setForeground(3, QtGui.QColor(client.instance.getColor("default")))
                
            self.myTree.addTopLevelItem(bucket_item)
            #self.myTree.setFirstItemColumnSpanned(bucket_item, True)
                
            for replay in buckets[bucket]:
                bucket_item.addChild(replay)

    def displayReplay(self):
        for uid in self.games:
            item = self.games[uid]
            if time.time() - item.info.get('launched_at', time.time()) > LIVEREPLAY_DELAY_TIME and item.isHidden():
                item.setHidden(False)

    @QtCore.pyqtSlot(dict)
    def processGameInfo(self, info):
        if info['state'] == "playing":
            if info['uid'] in self.games:
                # Updating an existing item
                item = self.games[info['uid']]
                
                item.takeChildren()  # Clear the children of this item before we're updating it
            else:
                # Creating a fresh item
                item = LiveReplayItem(info.get('launched_at', time.time()))
                self.games[info['uid']] = item
                
                self.liveTree.insertTopLevelItem(0, item)
                
                if time.time() - info.get('launched_at', time.time()) < LIVEREPLAY_DELAY_TIME:
                    item.setHidden(True)
                    # to get the delay right on client start, subtract the already passed game time
                    delay_time = LIVEREPLAY_DELAY_QTIMER - int(1000*(time.time() - info.get('launched_at', time.time())))
                    QtCore.QTimer.singleShot(delay_time, self.displayReplay)
                    # The delay is there because we have a delay in the livereplay server

            # For debugging purposes, format our tooltip for the top level items
            # so it contains a human-readable representation of the info dictionary
            item.info = info
            tip = ""            
            for key in list(info.keys()):
                tip += "'" + str(key) + "' : '" + str(info[key]) + "'<br/>"
                             
            item.setToolTip(1, tip)
            
            icon = fa.maps.preview(info['mapname'])
            item.setToolTip(0, fa.maps.getDisplayName(info['mapname']))
            if not icon:           
                self.client.downloader.downloadMap(item.info['mapname'], item, True)
                icon = util.icon("games/unknown_map.png")

            item.setText(0, time.strftime("%Y-%m-%d  -  %H:%M", time.localtime(item.info.get('launched_at', time.time()))))
            item.setForeground(0, QtGui.QColor(client.instance.getColor("default")))
                                    
            if info['featured_mod'] == "coop":  # no map icons for coop
                item.setIcon(0, util.icon("games/unknown_map.png"))
            else:
                item.setIcon(0, icon)
            if info['featured_mod'] == "ladder1v1":
                item.setText(1, info['title'])
            else:
                item.setText(1, info['title'] + "    -    [host: " + info['host'] + "]")
            item.setForeground(1, QtGui.QColor(client.instance.getColor("player")))
            
            item.setText(2, info['featured_mod'])
            item.setTextAlignment(2, QtCore.Qt.AlignCenter)

            if not info['teams']:
                item.setDisabled(True)

            # This game is the game the player is currently in
            mygame = False            

            # Create player entries for all the live players in a match
            for team in info['teams']:
                if team == "-1":  # skip observers, they don't seem to stream livereplays
                    continue
                
                for name in info['teams'][team]:
                    playeritem = QtWidgets.QTreeWidgetItem()
                    playeritem.setText(0, name)

                    playerid = self.client.players.getID(name)

                    url = QtCore.QUrl()
                    url.setScheme("faflive")
                    url.setHost("lobby.faforever.com")
                    url.setPath(str(info["uid"]) + "/" + name + ".SCFAreplay")
                    query = QtCore.QUrlQuery()
                    query.addQueryItem("map", info["mapname"])
                    query.addQueryItem("mod", info["featured_mod"])
                    url.setQuery(query)

                    playeritem.url = url
                    if client.instance.login == name:
                        mygame = True
                        item.setTextColor(1, QtGui.QColor(client.instance.getColor("self")))
                        playeritem.setForeground(0, QtGui.QColor(client.instance.getColor("self")))
                        playeritem.setToolTip(0, url.toString())
                        playeritem.setIcon(0, util.icon("replays/replay.png"))                        
                    elif client.instance.players.isFriend(playerid):
                        if not mygame:
                            item.setForeground(1, QtGui.QColor(client.instance.getColor("friend")))
                        playeritem.setForeground(0, QtGui.QColor(client.instance.getColor("friend")))
                        playeritem.setToolTip(0, url.toString())
                        playeritem.setIcon(0, util.icon("replays/replay.png"))                        
                    elif client.instance.players.isPlayer(playerid):
                        playeritem.setForeground(0, QtGui.QColor(client.instance.getColor("player")))
                        playeritem.setToolTip(0, url.toString())
                        playeritem.setIcon(0, util.icon("replays/replay.png"))                        
                    else:
                        playeritem.setForeground(0, QtGui.QColor(client.instance.getColor("default")))
                        playeritem.setDisabled(True)

                    item.addChild(playeritem)
        elif info['state'] == "closed":
            if info['uid'] in self.games:
                self.liveTree.takeTopLevelItem(self.liveTree.indexOfTopLevelItem(self.games[info['uid']]))
                
    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem)
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
        actionReplay.triggered.connect(lambda: self.liveTreeDoubleClicked(item, 0))
        actionLink.triggered.connect(lambda: QtWidgets.QApplication.clipboard().setText(item.toolTip(0)))
      
        # Adding to menu
        menu.addAction(actionReplay)
        menu.addAction(actionLink)
    
        # Finally: Show the popup
        menu.popup(QtWidgets.QCursor.pos())

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem)
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
        actionReplay.triggered.connect(lambda: self.myTreeDoubleClicked(item, 0))
        actionExplorer.triggered.connect(lambda: util.showFileInFileBrowser(item.filename))
      
        # Adding to menu
        menu.addAction(actionReplay)
        menu.addAction(actionExplorer)

        # Finally: Show the popup
        menu.popup(QtWidgets.QCursor.pos())


    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def myTreeDoubleClicked(self, item, column):
        if item.isDisabled():
            return

        if self.myTree.indexOfTopLevelItem(item) == -1:
            replay(item.filename)
                
    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def liveTreeDoubleClicked(self, item, column):
        """ This slot launches a live replay from eligible items in liveTree """

        if item.isDisabled():
            return
        
        if self.liveTree.indexOfTopLevelItem(item) == -1:
            # Notify other modules that we're watching a replay
            self.client.viewingReplay.emit(item.url)
            replay(item.url)
            
    def connectToReplayVault(self):
        """ connect to the replay vault server """

        if self.replayVaultSocket.state() != QtNetwork.QAbstractSocket.ConnectedState and self.replayVaultSocket.state() != QtNetwork.QAbstractSocket.ConnectingState:
            self.replayVaultSocket.connectToHost(self.HOST, self.SOCKET)        

    def send(self, message):
        data = json.dumps(message)
        logger.debug("Outgoing JSON Message: " + data)
        self.writeToServer(data)

    @QtCore.pyqtSlot()
    def readDataFromServer(self):
        ins = QtCore.QDataStream(self.replayVaultSocket)        
        ins.setVersion(QtCore.QDataStream.Qt_4_2)
        
        while not ins.atEnd():
            if self.blockSize == 0:
                if self.replayVaultSocket.bytesAvailable() < 4:
                    return
                self.blockSize = ins.readUInt32()            
            if self.replayVaultSocket.bytesAvailable() < self.blockSize:
                return
            
            action = ins.readQString()
            self.process(action, ins)
            self.blockSize = 0

    def process(self, action, stream):
        logger.debug("Replay Vault Server: " + action)
        self.receiveJSON(action, stream)
        
    def receiveJSON(self, data_string, stream):
        """ A fairly pythonic way to process received strings as JSON messages. """

        try:
            message = json.loads(data_string)
            self._dispatcher.dispatch(message)
        except ValueError as e:
            logger.error("Error decoding json ")
            logger.error(e)
        
        self.replayVaultSocket.disconnectFromHost()
        
    def writeToServer(self, action, *args, **kw):
        logger.debug(("writeToServer(" + action + ", [" + ', '.join(args) + "])"))
        
        block = QtCore.QByteArray()
        out = QtCore.QDataStream(block, QtCore.QIODevice.ReadWrite)
        out.setVersion(QtCore.QDataStream.Qt_4_2)
        out.writeUInt32(0)
        out.writeQString(action)
        
        for arg in args:
            if type(arg) is int:
                out.writeInt(arg)
            elif isinstance(arg, str):
                out.writeQString(arg)
            elif type(arg) is float:
                out.writeFloat(arg)
            elif type(arg) is list:
                out.writeQVariantList(arg)
            else:
                logger.warn("Uninterpreted Data Type: " + str(type(arg)) + " of value: " + str(arg))
                out.writeQString(str(arg))

        out.device().seek(0)
        out.writeUInt32(block.size() - 4)

        self.bytesToSend = block.size() - 4        
        self.replayVaultSocket.write(block)

    def handleServerError(self, socketError):
        if socketError == QtNetwork.QAbstractSocket.RemoteHostClosedError:
            logger.info("Replay Server down: The server is down for maintenance, please try later.")

        elif socketError == QtNetwork.QAbstractSocket.HostNotFoundError:
            logger.info("Connection to Host lost. Please check the host name and port settings.")
            
        elif socketError == QtNetwork.QAbstractSocket.ConnectionRefusedError:
            logger.info("The connection was refused by the peer.")
        else:
            logger.info("The following error occurred: %s." % self.replayVaultSocket.errorString())    

    @QtCore.pyqtSlot()
    def disconnected(self):
        logger.debug("Disconnected from server")

    @QtCore.pyqtSlot(QtNetwork.QAbstractSocket.SocketError)
    def errored(self, error):
        logger.error("TCP Error " + self.replayVaultSocket.errorString())
