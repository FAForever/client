from PyQt4 import QtCore, QtGui
import util
from replays import logger
import os
import fa
import time
import client
import json

# Replays uses the new Inheritance Based UI creation pattern
# This allows us to do all sorts of awesome stuff by overriding methods etc.

FormClass, BaseClass = util.loadUiType("replays/replays.ui")

class ReplaysWidget(BaseClass, FormClass):

    def __init__(self, client):
        super(BaseClass, self).__init__()

        self.setupUi(self)

        #self.replayVault.setVisible(False)
        self.client = client
        client.replaysTab.layout().addWidget(self)
        
        client.gameInfo.connect(self.processGameInfo)
            
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
        
        logger.info("Replays Widget instantiated.")

        # Old replay vault code adapted to this.                
        self.loaded = False
        self.client.showReplays.connect(self.reloadView)
        self.webView.loadFinished.connect(self.webView.show)

        
    @QtCore.pyqtSlot()
    def reloadView(self):
        if (self.loaded):
            return
        self.loaded = True
        
        #self.webView.setVisible(False)

        #If a local theme CSS exists, skin the WebView with it
        if util.themeurl("vault/style.css"):
            self.webView.settings().setUserStyleSheetUrl(util.themeurl("vault/style.css"))
        self.webView.setUrl(QtCore.QUrl("http://www.faforever.com/webcontent/replayvault?username={user}&pwdhash={pwdhash}".format(user=self.client.login, pwdhash=self.client.password)))
        
        
    def focusEvent(self, event):
        self.updatemyTree()
        return BaseClass.focusEvent(self, event)
    
    def showEvent(self, event):
        self.updatemyTree()
        return BaseClass.showEvent(self, event)

                
                
    def updatemyTree(self):
        self.myTree.clear()
        
        # We put the replays into buckets by day first, then we add them to the treewidget.
        buckets = {}
        
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
                    item.info = json.loads(open(item.filename, "rt").readline())
                    
                    # Parse replayinfo into data
                    if item.info.get('complete', False):
                        game_date = time.strftime("%Y-%m-%d", time.localtime(item.info['game_time']))
                        game_hour = time.strftime("%H:%M", time.localtime(item.info['game_time']))
                        
                        bucket = buckets.setdefault(game_date, [])                    
                        
                        item.setIcon(0, fa.maps.preview(item.info['mapname']))
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
                        item.setTextColor(1, QtGui.QColor(client.instance.getUserColor(item.info.get('recorder', ""))))
                    else:
                        bucket = buckets.setdefault("incomplete", [])                    
                        item.setIcon(0, util.icon("replays/replay.png"))
                        item.setText(1, infile)
                        item.setText(2, "(replay doesn't have complete metadata)")
                        item.setTextColor(1, QtGui.QColor("yellow")) #FIXME: Needs to come from theme

                except:
                    bucket = buckets.setdefault("broken", [])                    
                    item.setIcon(0, util.icon("replays/broken.png"))
                    item.setText(1, infile)
                    item.setTextColor(1, QtGui.QColor("red"))   #FIXME: Needs to come from theme
                    item.setText(2, "(replay parse error)")
                    item.setTextColor(2, QtGui.QColor("gray"))  #FIXME: Needs to come from theme
                    logger.error("Replay parse error for " + infile)

                bucket.append(item)
                    
                
            
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
                icon = util.icon("games/unknown_map.png")

            item.setText(0,time.strftime("%H:%M", time.localtime(item.info['game_time'])))
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
                    url.setHost("faforever.com")
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
                    elif client.instance.isFriend(player):
                        if not mygame:
                            item.setTextColor(1, QtGui.QColor(client.instance.getColor("friend")))
                        playeritem.setTextColor(0, QtGui.QColor(client.instance.getColor("friend")))
                        playeritem.setToolTip(0, url.toString())
                        playeritem.setIcon(0, util.icon("replays/replay.png"))                        
                    elif client.instance.isPlayer(player):
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
            fa.exe.replay(item.filename)
                
                
    @QtCore.pyqtSlot(QtGui.QTreeWidgetItem, int)
    def liveTreeDoubleClicked(self, item, column):
        '''
        This slot launches a live replay from eligible items in liveTree
        '''
        if item.isDisabled():
            return
        
        if self.liveTree.indexOfTopLevelItem(item) == -1:
            fa.exe.replay(item.url)
            
    