



from PyQt4 import QtCore, QtGui, QtNetwork
from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from fa.replay import replay
import util
import os
import fa
import time
import client
import json

import logging
logger = logging.getLogger(__name__)

LIVEREPLAY_DELAY = 5 #livereplay delay in minutes
LIVEREPLAY_DELAY_TIME = LIVEREPLAY_DELAY * 60 #livereplay delay for time() (in seconds)
LIVEREPLAY_DELAY_QTIMER = LIVEREPLAY_DELAY * 60000 #livereplay delay for Qtimer (in milliseconds)

from replays.replayitem import ReplayItem, ReplayItemDelegate

# Replays uses the new Inheritance Based UI creation pattern
# This allows us to do all sorts of awesome stuff by overriding methods etc.

FormClass, BaseClass = util.loadUiType("replays/replays.ui")

class ReplaysWidget(BaseClass, FormClass):
    SOCKET  = 11002
    HOST    = "lobby.faforever.com"
    
    def __init__(self, client):
        super(BaseClass, self).__init__()

        self.setupUi(self)

        #self.replayVault.setVisible(False)
        self.client = client
        client.replaysTab.layout().addWidget(self)
        
        client.gameInfo.connect(self.processGameInfo)
        client.replayVault.connect(self.replayVault)    
        
        self.onlineReplays = {}
        self.onlineTree.setItemDelegate(ReplayItemDelegate(self))
        self.replayDownload = QNetworkAccessManager()
        self.replayDownload.finished.connect(self.finishRequest)
        
        # sending request to replay vault
        self.searchButton.pressed.connect(self.searchVault)
        self.playerName.returnPressed.connect(self.searchVault)
        self.mapName.returnPressed.connect(self.searchVault)
        self.spoilerCheckbox.stateChanged.connect(self.spoilerCheckboxPressed)

        self.myTree.itemDoubleClicked.connect(self.myTreeDoubleClicked)
        self.myTree.itemPressed.connect(self.myTreePressed)
        self.myTree.header().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        self.myTree.header().setResizeMode(1, QtGui.QHeaderView.ResizeToContents)
        self.myTree.header().setResizeMode(2, QtGui.QHeaderView.Stretch)
        self.myTree.header().setResizeMode(3, QtGui.QHeaderView.ResizeToContents)
        
        self.liveTree.itemDoubleClicked.connect(self.liveTreeDoubleClicked)
        self.liveTree.itemPressed.connect(self.liveTreePressed)
        self.liveTree.header().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        self.liveTree.header().setResizeMode(1, QtGui.QHeaderView.Stretch)
        self.liveTree.header().setResizeMode(2, QtGui.QHeaderView.ResizeToContents)
        
        self.games = {}
        
        self.onlineTree.itemDoubleClicked.connect(self.onlineTreeDoubleClicked)
        self.onlineTree.itemPressed.connect(self.onlineTreeClicked)
        self.selectedReplay = False

        # replay vault connection to server
        self.searching = False
        self.blockSize = 0
        self.replayVaultSocket = QtNetwork.QTcpSocket()
        self.replayVaultSocket.error.connect(self.handleServerError)
        self.replayVaultSocket.readyRead.connect(self.readDataFromServer)
        self.replayVaultSocket.disconnected.connect(self.disconnected)
        self.replayVaultSocket.error.connect(self.errored) 

        
        logger.info("Replays Widget instantiated.")

        
    def searchVault(self):
        ''' search for some replays '''
        self.searching = True
        self.connectToModVault()
        self.send(dict(command="search", rating = self.minRating.value(), map = self.mapName.text(), player = self.playerName.text(), mod = self.modList.currentText()))
        self.onlineTree.clear()

    def reloadView(self):
        if self.searching != True:
            self.connectToModVault()
            self.send(dict(command="list"))
        

    def finishRequest(self, reply):
        if reply.error() != QNetworkReply.NoError:
            QtGui.QMessageBox.warning(self, "Network Error", reply.errorString())
        else:
            faf_replay = QtCore.QFile(os.path.join(util.CACHE_DIR, "temp.fafreplay"))
            faf_replay.open(QtCore.QIODevice.WriteOnly | QtCore.QIODevice.Truncate)                
            faf_replay.write(reply.readAll())
            faf_replay.flush()
            faf_replay.close()  
            replay(os.path.join(util.CACHE_DIR, "temp.fafreplay"))

    def onlineTreeClicked(self, item):
        if QtGui.QApplication.mouseButtons() == QtCore.Qt.RightButton:
            if type(item.parent) == ReplaysWidget:
                item.pressed(item)
        else:
            self.selectedReplay = item
            if hasattr(item, "moreInfo"):
                if item.moreInfo is False:
                    self.connectToModVault()
                    self.send(dict(command="info_replay", uid=item.uid))
                elif item.spoiled != self.spoilerCheckbox.isChecked():
                    self.replayInfos.clear()
                    self.replayInfos.setHtml(item.replayInfo)
                else:
                    self.replayInfos.clear()
                    item.generateInfoPlayersHtml()
                
    def onlineTreeDoubleClicked(self, item):
        if hasattr(item, "url") :
            self.replayDownload.get(QNetworkRequest(QtCore.QUrl(item.url))) 

    def spoilerCheckboxPressed(self, item):
        if self.selectedReplay:
            self.selectedReplay.generateInfoPlayersHtml()

    def replayVault(self, message):
        action = message["action"]
        if action == "list_recents" :
            self.onlineReplays = {}
            replays = message["replays"]
            for replay in replays :
                uid = replay["id"]
        
                if uid not in self.onlineReplays:
                    self.onlineReplays[uid] = ReplayItem(uid, self)
                    self.onlineReplays[uid].update(replay, self.client)
                else:
                    self.onlineReplays[uid].update(replay, self.client)
                    
            self.updateOnlineTree()
            
        elif action == "info_replay" :
            uid = message["uid"]
            if uid in self.onlineReplays:
                self.onlineReplays[uid].infoPlayers(message["players"])
                
        elif action == "search_result" :
            self.searching = False
            self.onlineReplays = {}
            replays = message["replays"]
            for replay in replays :
                uid = replay["id"]
        
                if uid not in self.onlineReplays:
                    self.onlineReplays[uid] = ReplayItem(uid, self)
                    self.onlineReplays[uid].update(replay, self.client)
                else:
                    self.onlineReplays[uid].update(replay, self.client)
                    
            self.updateOnlineTree()

    def focusEvent(self, event):
        self.updatemyTree()
        self.reloadView()
        return BaseClass.focusEvent(self, event)
    
    def showEvent(self, event):
        self.updatemyTree()
        self.reloadView()
        return BaseClass.showEvent(self, event)

                
    def updateOnlineTree(self):
        self.replayInfos.clear()
        self.onlineTree.clear()
        buckets = {}
        for uid in self.onlineReplays :
            bucket = buckets.setdefault(self.onlineReplays[uid].startDate, [])
            bucket.append(self.onlineReplays[uid])
            
        for bucket in buckets.keys():
            bucket_item = QtGui.QTreeWidgetItem()
            self.onlineTree.addTopLevelItem(bucket_item)
            
            bucket_item.setIcon(0, util.icon("replays/bucket.png"))                                
            bucket_item.setText(0, "<font color='white'>" + bucket+"</font>")
            bucket_item.setText(1,"<font color='white'>" + str(len(buckets[bucket])) + " replays</font>")
            
            
            
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
            for filename, metadata in cache_hit.iteritems():
                fh.write(filename + ":" + metadata)
            for filename, metadata in cache_add.iteritems():
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
                
                item = QtGui.QTreeWidgetItem()
                item.setText(1, infile)
                item.filename = os.path.join(util.REPLAY_DIR, infile)
                item.setIcon(0, util.icon("replays/replay.png"))
                item.setTextColor(0, QtGui.QColor(client.instance.getColor("default")))
                                
                bucket.append(item)
                
            elif infile.endswith(".fafreplay"):
                item = QtGui.QTreeWidgetItem()
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
                            item.setIcon(0,util.icon("games/unknown_map.png"))                                                      
                        item.setToolTip(0, fa.maps.getDisplayName(item.info['mapname']))
                        item.setText(0, game_hour)
                        item.setTextColor(0, QtGui.QColor(client.instance.getColor("default")))
                        
                        item.setText(1, item.info['title'])
                        item.setToolTip(1, infile)
    
                        # Hacky way to quickly assemble a list of all the players, but including the observers
                        playerlist = []
                        for _, players in item.info['teams'].items():
                            playerlist.extend(players)
                        item.setText(2, ", ".join(playerlist))
                        item.setToolTip(2, ", ".join(playerlist))
                        
                        # Add additional info
                        item.setText(3, item.info['featured_mod'])
                        item.setTextAlignment(3, QtCore.Qt.AlignCenter)
                        item.setTextColor(1, QtGui.QColor(client.instance.players.getUserColor(item.info.get('recorder', ""))))
                    else:
                        bucket = buckets.setdefault("incomplete", [])                    
                        item.setIcon(0, util.icon("replays/replay.png"))
                        item.setText(1, infile)
                        item.setText(2, "(replay doesn't have complete metadata)")
                        item.setTextColor(1, QtGui.QColor("yellow")) #FIXME: Needs to come from theme

                except Exception as ex:
                    bucket = buckets.setdefault("broken", [])                    
                    item.setIcon(0, util.icon("replays/broken.png"))
                    item.setText(1, infile)
                    item.setTextColor(1, QtGui.QColor("red"))   #FIXME: Needs to come from theme
                    item.setText(2, "(replay parse error)")
                    item.setTextColor(2, QtGui.QColor("gray"))  #FIXME: Needs to come from theme
                    logger.exception("Exception parsing replay {}: {}".format(infile, ex))

                bucket.append(item)

        if len(cache_add) > 10 or len(cache) - len(cache_hit) > 10:
            self.saveLocalCache(cache_hit, cache_add)
        # Now, create a top level treewidgetitem for every bucket, and put the bucket's contents into them         
        for bucket in buckets.keys():
            bucket_item = QtGui.QTreeWidgetItem()
            
            if bucket == "broken":
                bucket_item.setTextColor(0, QtGui.QColor("red")) #FIXME: Needs to come from theme
                bucket_item.setText(1, "(not watchable)")
                bucket_item.setTextColor(1, QtGui.QColor(client.instance.getColor("default")))
            elif bucket == "incomplete":
                bucket_item.setTextColor(0, QtGui.QColor("yellow")) #FIXME: Needs to come from theme
                bucket_item.setText(1, "(watchable)")
                bucket_item.setTextColor(1, QtGui.QColor(client.instance.getColor("default")))
            elif bucket == "legacy":
                bucket_item.setTextColor(0, QtGui.QColor(client.instance.getColor("default")))
                bucket_item.setTextColor(1, QtGui.QColor(client.instance.getColor("default")))
                bucket_item.setText(1, "(old replay system)")
            else:
                bucket_item.setTextColor(0, QtGui.QColor(client.instance.getColor("player")))
                
            bucket_item.setIcon(0, util.icon("replays/bucket.png"))                                
            bucket_item.setText(0, bucket)
            bucket_item.setText(3, str(len(buckets[bucket])) + " replays")
            bucket_item.setTextColor(3, QtGui.QColor(client.instance.getColor("default")))
                
            self.myTree.addTopLevelItem(bucket_item)
            #self.myTree.setFirstItemColumnSpanned(bucket_item, True)
                
            for replay in buckets[bucket]:
                bucket_item.addChild(replay)


    def displayReplay(self):
        for uid in self.games :
            item = self.games[uid]
            if time.time() - item.info.get('launched_at', time.time()) > LIVEREPLAY_DELAY_TIME and item.isHidden():
                item.setHidden(False)

    @QtCore.pyqtSlot(dict)
    def processGameInfo(self, info):
        if info['state'] == "playing":
            if info['uid'] in self.games:
                # Updating an existing item
                item = self.games[info['uid']]
                
                item.takeChildren()  #Clear the children of this item before we're updating it
            else:
                # Creating a fresh item
                item = QtGui.QTreeWidgetItem()
                self.games[info['uid']] = item
                
                self.liveTree.insertTopLevelItem(0, item)
                
                if time.time() - info.get('launched_at', time.time()) < LIVEREPLAY_DELAY_TIME:
                    item.setHidden(True)
                    QtCore.QTimer.singleShot(LIVEREPLAY_DELAY_QTIMER, self.displayReplay) #The delay is there because we have a delay in the livereplay server

            # For debugging purposes, format our tooltip for the top level items
            # so it contains a human-readable representation of the info dictionary
            item.info = info
            tip = ""            
            for key in info.keys():
                tip += "'" + unicode(key) + "' : '" + unicode(info[key]) + "'<br/>"
                             
            item.setToolTip(1, tip)
            
            icon = fa.maps.preview(info['mapname'])
            item.setToolTip(0, fa.maps.getDisplayName(info['mapname']))
            if not icon:           
                self.client.downloader.downloadMap(item.info['mapname'], item, True)
                icon = util.icon("games/unknown_map.png")

            item.setText(0,time.strftime("%H:%M", time.localtime(item.info.get('launched_at', time.time()))))
            item.setTextColor(0, QtGui.QColor(client.instance.getColor("default")))
                                    

            item.setIcon(0, icon)
            item.setText(1, info['title'])
            item.setTextColor(1, QtGui.QColor(client.instance.getColor("player")))
            
            item.setText(2, info['featured_mod'])
            item.setTextAlignment(2, QtCore.Qt.AlignCenter)

            if not info['teams']:
                item.setDisabled(True)

            # This game is the game the player is currently in
            mygame = False            

            # Create player entries for all the live players in a match
            for team in info['teams']:
                if team == "-1": #skip observers, they don't seem to stream livereplays
                    continue
                
                for player in info['teams'][team]:
                    playeritem = QtGui.QTreeWidgetItem()
                    playeritem.setText(0, player)  

                    url = QtCore.QUrl()
                    url.setScheme("faflive")
                    url.setHost("lobby.faforever.com")
                    url.setPath(str(info["uid"]) + "/" + player + ".SCFAreplay")
                    url.addQueryItem("map", info["mapname"])
                    url.addQueryItem("mod", info["featured_mod"])
                    
                    playeritem.url = url
                    if client.instance.login == player:
                        mygame = True
                        item.setTextColor(1, QtGui.QColor(client.instance.getColor("self")))
                        playeritem.setTextColor(0, QtGui.QColor(client.instance.getColor("self")))
                        playeritem.setToolTip(0, url.toString())
                        playeritem.setIcon(0, util.icon("replays/replay.png"))                        
                    elif client.instance.players.isFriend(player):
                        if not mygame:
                            item.setTextColor(1, QtGui.QColor(client.instance.getColor("friend")))
                        playeritem.setTextColor(0, QtGui.QColor(client.instance.getColor("friend")))
                        playeritem.setToolTip(0, url.toString())
                        playeritem.setIcon(0, util.icon("replays/replay.png"))                        
                    elif client.instance.players.isPlayer(player):
                        playeritem.setTextColor(0, QtGui.QColor(client.instance.getColor("player")))                        
                        playeritem.setToolTip(0, url.toString())
                        playeritem.setIcon(0, util.icon("replays/replay.png"))                        
                    else:
                        playeritem.setTextColor(0, QtGui.QColor(client.instance.getColor("default")))
                        playeritem.setDisabled(True)

                    item.addChild(playeritem)
                    self.liveTree.setFirstItemColumnSpanned(playeritem, True)
        elif info['state'] == "closed":
            if info['uid'] in self.games:
                self.liveTree.takeTopLevelItem(self.liveTree.indexOfTopLevelItem(self.games[info['uid']]))
                
                
                
    @QtCore.pyqtSlot(QtGui.QTreeWidgetItem)
    def liveTreePressed(self, item):
        if QtGui.QApplication.mouseButtons() != QtCore.Qt.RightButton:
            return            
            
        if self.liveTree.indexOfTopLevelItem(item) != -1:
            item.setExpanded(True)
            return

        menu = QtGui.QMenu(self.liveTree)
        
        # Actions for Games and Replays
        actionReplay = QtGui.QAction("Replay in FA", menu)
        actionLink = QtGui.QAction("Copy Link", menu)
        
        # Adding to menu
        menu.addAction(actionReplay)
        menu.addAction(actionLink)
            
        # Triggers
        actionReplay.triggered.connect(lambda : self.liveTreeDoubleClicked(item, 0))
        actionLink.triggered.connect(lambda : QtGui.QApplication.clipboard().setText(item.toolTip(0)))
      
        # Adding to menu
        menu.addAction(actionReplay)
        menu.addAction(actionLink)
    
        #Finally: Show the popup
        menu.popup(QtGui.QCursor.pos())


    
    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def myTreePressed(self, item):
        if QtGui.QApplication.mouseButtons() != QtCore.Qt.RightButton:
            return
                    
        if item.isDisabled():
            return

        if self.myTree.indexOfTopLevelItem(item) != -1:
            return
        
        menu = QtGui.QMenu(self.myTree)
        
        # Actions for Games and Replays
        actionReplay = QtGui.QAction("Replay", menu)
        actionExplorer = QtGui.QAction("Show in Explorer", menu)
        
        # Adding to menu
        menu.addAction(actionReplay)
        menu.addAction(actionExplorer)
            
        # Triggers
        actionReplay.triggered.connect(lambda : self.myTreeDoubleClicked(item, 0))
        actionExplorer.triggered.connect(lambda : util.showInExplorer(item.filename))
      
        # Adding to menu
        menu.addAction(actionReplay)
        menu.addAction(actionExplorer)

        #Finally: Show the popup
        menu.popup(QtGui.QCursor.pos())




    @QtCore.pyqtSlot(QtGui.QTreeWidgetItem, int)
    def myTreeDoubleClicked(self, item, column):
        if item.isDisabled():
            return

        if self.myTree.indexOfTopLevelItem(item) == -1:
            replay(item.filename)
                
                
    @QtCore.pyqtSlot(QtGui.QTreeWidgetItem, int)
    def liveTreeDoubleClicked(self, item, column):
        '''
        This slot launches a live replay from eligible items in liveTree
        '''
        if item.isDisabled():
            return
        
        if self.liveTree.indexOfTopLevelItem(item) == -1:
            # Notify other modules that we're watching a replay
            self.client.viewingReplay.emit(item.url)
            replay(item.url)
            
    def connectToModVault(self):
        ''' connect to the replay vault server'''
        
        if self.replayVaultSocket.state() != QtNetwork.QAbstractSocket.ConnectedState and self.replayVaultSocket.state() !=QtNetwork.QAbstractSocket.ConnectingState:
            self.replayVaultSocket.connectToHost(self.HOST, self.SOCKET)        
    
    
    def send(self, message):
        data = json.dumps(message)
        logger.debug("Outgoing JSON Message: " + data)
        self.writeToServer(data)

    @QtCore.pyqtSlot()
    def readDataFromServer(self):
        ins = QtCore.QDataStream(self.replayVaultSocket)        
        ins.setVersion(QtCore.QDataStream.Qt_4_2)
        
        while ins.atEnd() == False :
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
        '''
        A fairly pythonic way to process received strings as JSON messages.
        '''
        try:
            message = json.loads(data_string)
            cmd = "handle_" + message['command']
            if hasattr(self.client, cmd):
                getattr(self.client, cmd)(message)
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
        
        for arg in args :            
            if type(arg) is IntType:
                out.writeInt(arg)
            elif isinstance(arg, basestring):
                out.writeQString(arg)
            elif type(arg) is FloatType:
                out.writeFloat(arg)
            elif type(arg) is ListType:
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
