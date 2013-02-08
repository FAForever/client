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





from PyQt4 import QtCore, QtGui
from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkRequest
from games.moditem import mods 
import util
from replays import logger
import os
import fa
import time
import client
import json

from replays.replayitem import ReplayItem, ReplayItemDelegate

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
        client.replayVault.connect(self.replayVault)    
        
        self.onlineReplays = {}
        self.onlineTree.setItemDelegate(ReplayItemDelegate(self))
        self.replayDownload = QNetworkAccessManager()
        self.replayDownload.finished.connect(self.finishRequest)
        self.searchButton.pressed.connect(self.searchVault)
        
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
        self.onlineTree.itemClicked.connect(self.onlineTreeClicked)
        logger.info("Replays Widget instantiated.")

        
    def searchVault(self):
        self.client.send(dict(command="replay_vault", action="search", rating = self.minRating.value(), map = self.mapName.text(), player = self.playerName.text(), mod = self.modList.currentText()))
        self.onlineTree.clear()

    def reloadView(self):         
        self.client.send(dict(command="replay_vault", action="list"))

    def finishRequest(self, reply):
        faf_replay = QtCore.QFile(os.path.join(util.CACHE_DIR, "temp.fafreplay"))
        faf_replay.open(QtCore.QIODevice.WriteOnly | QtCore.QIODevice.Truncate)                
        faf_replay.write(reply.readAll())
        faf_replay.flush()
        faf_replay.close()  
        fa.exe.replay(os.path.join(util.CACHE_DIR, "temp.fafreplay"))

    def onlineTreeClicked(self, item):
        if hasattr(item, "moreInfo") :
            if item.moreInfo == False :
                self.client.send(dict(command="replay_vault", action="info_replay", uid = item.uid))
            else :
                self.replayInfos.clear()
                self.replayInfos.setHtml(item.replayInfo)
                
    def onlineTreeDoubleClicked(self, item):
        if hasattr(item, "url") :
            self.replayDownload.get(QNetworkRequest(QtCore.QUrl(item.url))) 


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
            
    
