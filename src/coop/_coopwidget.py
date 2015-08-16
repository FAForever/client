from PyQt4 import QtCore, QtGui
import fa
from fa.replay import replay
from fa.wizards import WizardSC
import util

from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkRequest

from games.gameitem import GameItem, GameItemDelegate
from coop.coopmapitem import CoopMapItem, CoopMapItemDelegate
from games.hostgamewidget import HostgameWidget
from fa import faction
import random
import fa
import modvault
import os

import logging
logger = logging.getLogger(__name__)


FormClass, BaseClass = util.loadUiType("coop/coop.ui")


class CoopWidget(FormClass, BaseClass):
    def __init__(self, client, *args, **kwargs):
        
        BaseClass.__init__(self, *args, **kwargs)        
        
        self.setupUi(self)

        self.client = client
        self.client.coopTab.layout().addWidget(self)
        
        #Dictionary containing our actual games.
        self.games = {}
        
        #Ranked search UI
        self.ispassworded = False
        self.loaded = False
        
        self.coop = {}
        self.cooptypes = {}
        
        self.canChooseMap = False
        self.options = []
        
        self.client.showCoop.connect(self.coopChanged)
        self.client.coopInfo.connect(self.processCoopInfo)
        self.client.gameInfo.connect(self.processGameInfo)
        self.coopList.header().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        self.coopList.setItemDelegate(CoopMapItemDelegate(self))
        
        
        self.gameList.setItemDelegate(GameItemDelegate(self))
        self.gameList.itemDoubleClicked.connect(self.gameDoubleClicked)

        self.coopList.itemDoubleClicked.connect(self.coopListDoubleClicked)
        self.coopList.itemClicked.connect(self.coopListClicked)
        
        self.client.coopLeaderBoard.connect(self.processLeaderBoardInfos)
        self.tabLeaderWidget.currentChanged.connect(self.askLeaderBoard)
        
        self.linkButton.clicked.connect(self.linkVanilla)
        #Load game name from settings (yay, it's persistent!)        
        self.loadGameName()
        self.loadPassword()
        self.leaderBoard.setVisible(0)
        self.stylesheet              = util.readstylesheet("coop/formatters/style.css")
        self.FORMATTER_LADDER        = unicode(util.readfile("coop/formatters/ladder.qthtml"))
        self.FORMATTER_LADDER_HEADER = unicode(util.readfile("coop/formatters/ladder_header.qthtml"))

        self.leaderBoard.setStyleSheet(self.stylesheet)
        
        self.leaderBoardTextGeneral.anchorClicked.connect(self.openUrl)
        self.leaderBoardTextOne.anchorClicked.connect(self.openUrl)
        self.leaderBoardTextTwo.anchorClicked.connect(self.openUrl)
        self.leaderBoardTextThree.anchorClicked.connect(self.openUrl)
        self.leaderBoardTextFour.anchorClicked.connect(self.openUrl)

        self.replayDownload = QNetworkAccessManager()
        self.replayDownload.finished.connect(self.finishRequest)

    
        self.selectedItem = None

    @QtCore.pyqtSlot(QtCore.QUrl)
    def openUrl(self, url):
        self.replayDownload.get(QNetworkRequest(url))

    def finishRequest(self, reply):
        faf_replay = QtCore.QFile(os.path.join(util.CACHE_DIR, "temp.fafreplay"))
        faf_replay.open(QtCore.QIODevice.WriteOnly | QtCore.QIODevice.Truncate)                
        faf_replay.write(reply.readAll())
        faf_replay.flush()
        faf_replay.close()  
        replay(os.path.join(util.CACHE_DIR, "temp.fafreplay"))
        
    def processLeaderBoardInfos(self, message):
        ''' Process leaderboard'''

        values = message["leaderboard"]
        table = message["table"]
        if table == 0:
            w = self.leaderBoardTextGeneral
        elif table == 1:
            w = self.leaderBoardTextOne
        elif table == 2:
            w = self.leaderBoardTextTwo
        elif table == 3:
            w = self.leaderBoardTextThree
        elif table == 4:
            w = self.leaderBoardTextFour

                        
        doc = QtGui.QTextDocument()
        doc.addResource(3, QtCore.QUrl("style.css"), self.stylesheet )
        html = ("<html><head><link rel='stylesheet' type='text/css' href='style.css'></head><body>")
        
        if self.selectedItem:
            html += '<p class="division" align="center">'+self.selectedItem.name+'</p><hr/>'
        html +="<table class='players' cellspacing='0' cellpadding='0' width='630' height='100%'>"

        formatter = self.FORMATTER_LADDER
        formatter_header = self.FORMATTER_LADDER_HEADER
        cursor = w.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        w.setTextCursor(cursor) 
        color = "lime"
        line = formatter_header.format(rank="rank", names="names", time="time", color=color)
        html += line
        rank = 1
        for val in values :
            #val = values[uid]
            players = ", ".join(val["players"]) 
            numPlayers = str(len(val["players"]))
            timing = val["time"]
            gameuid = str(val["gameuid"])
            if val["secondary"] == 1:
                secondary = "Yes"
            else:
                secondary = "No"
            if rank % 2 == 0 :
                line = formatter.format(rank=str(rank), numplayers=numPlayers, gameuid=gameuid, players= players, objectives=secondary, timing=timing, type="even")
            else :
                line = formatter.format(rank=str(rank), numplayers=numPlayers, gameuid=gameuid, players= players, objectives=secondary, timing=timing, type="")
            
            rank = rank + 1
            
            html += line

        html +="</tbody></table></body></html>"

        doc.setHtml(html)
        w.setDocument(doc)
        
        self.leaderBoard.setVisible(True)
    
    @QtCore.pyqtSlot()
    def linkVanilla(self):    
        WizardSC(self).exec_()

    def coopChanged(self):
        if not self.loaded:
            self.client.send(dict(command="coop_list"))
            self.loaded = True

    def askLeaderBoard(self):
        ''' 
        ask the server for stats
        '''
        if self.selectedItem:
            self.client.statsServer.send(dict(command="coop_stats", mission=self.selectedItem.uid, type=self.tabLeaderWidget.currentIndex()))

    def coopListClicked(self, item):
        '''
        Hosting a coop event
        '''
        if not hasattr(item, "mapUrl") :
            if item.isExpanded():
                item.setExpanded(False)
            else:
                item.setExpanded(True)
            return

        if item != self.selectedItem: 
            self.selectedItem = item
            self.client.statsServer.send(dict(command="coop_stats", mission=item.uid, type=self.tabLeaderWidget.currentIndex()))

    def coopListDoubleClicked(self, item):
        '''
        Hosting a coop event
        '''
        if not hasattr(item, "mapUrl") :
            return
        
        if not fa.instance.available():
            return
            
        self.client.games.stopSearchRanked()
        self.gamemap = fa.maps.link2name(item.mapUrl)
        
        fa.check.map(self.gamemap, force=True)
        
        # A simple Hosting dialog.
        if fa.check.check("coop"):
            hostgamewidget = HostgameWidget(self, item)
            
            if hostgamewidget.exec_() == 1 :
                if self.gamename:
                    modnames = [str(moditem.text()) for moditem in hostgamewidget.modList.selectedItems()]
                    mods = [hostgamewidget.mods[modstr] for modstr in modnames]
                    modvault.setActiveMods(mods, True) #should be removed later as it should be managed by the server.
#                #Send a message to the server with our intent.
                    if self.ispassworded:
                        self.client.send(dict(command="game_host", access="password", password = self.gamepassword, mod=item.mod, title=self.gamename, mapname=self.gamemap, gameport=self.client.gamePort))
                    else :
                        self.client.send(dict(command="game_host", access="public", mod=item.mod, title=self.gamename, mapname=self.gamemap, gameport=self.client.gamePort))


    @QtCore.pyqtSlot(dict)
    def processCoopInfo(self, message): 
        '''
        Slot that interprets and propagates coop_info messages into the coop list 
        ''' 
        uid = message["uid"]
      
        
        if uid not in self.coop:
            typeCoop = message["type"]
            
            if not typeCoop in self.cooptypes:
                root_item = QtGui.QTreeWidgetItem()
                self.coopList.addTopLevelItem(root_item)
                root_item.setText(0, "<font color='white' size=+3>%s</font>" % typeCoop)
                self.cooptypes[typeCoop] = root_item
                root_item.setExpanded(False)
            else:
                root_item = self.cooptypes[typeCoop] 
            
            itemCoop = CoopMapItem(uid, self)
            itemCoop.update(message)
            
            root_item.addChild(itemCoop)

            self.coop[uid] = itemCoop

            
    @QtCore.pyqtSlot(dict)
    def processGameInfo(self, message):
        '''
        Slot that interprets and propagates game_info messages into GameItems 
        '''
        uid = message["uid"]
        if message["featured_mod"] == "coop":
            if 'max_players' in  message:
                message["max_players"] = 4

            if uid not in self.games:
                self.games[uid] = GameItem(uid)
                self.gameList.addItem(self.games[uid])
                self.games[uid].update(message, self.client)
            else:
                self.games[uid].update(message, self.client)

            if message['state'] == "open":
                # force the display.
                self.games[uid].setHidden(False)    
    
        #Special case: removal of a game that has ended         
        if message['state'] == "closed":
            if uid in self.games:
                self.gameList.takeItem(self.gameList.row(self.games[uid]))
                del self.games[uid]    
            return

    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def gameDoubleClicked(self, item):
        '''
        Slot that attempts to join a game.
        '''
        if not fa.instance.available():
            return

        if not fa.check.check(item.mod, item.mapname, None, item.mods):
            return

        if item.access == "password" :
            passw, ok = QtGui.QInputDialog.getText(self.client, "Passworded game" , "Enter password :", QtGui.QLineEdit.Normal, "")
            if ok:
                self.client.send(dict(command="game_join", password=passw, uid=item.uid, gameport=self.client.gamePort))
        else :
            self.client.send(dict(command="game_join", uid=item.uid, gameport=self.client.gamePort))


    def savePassword(self, password):
        self.gamepassword = password
        util.settings.beginGroup("fa.games")
        util.settings.setValue("password", self.gamepassword)        
        util.settings.endGroup()        
                
                
    def loadPassword(self):
        util.settings.beginGroup("fa.games")
        self.gamepassword = util.settings.value("password", None)        
        util.settings.endGroup()        
                
        #Default Game Map ...
        if not self.gamepassword:
            self.gamepassword = "password"

    def saveGameMap(self, name):
        pass
                

    def saveGameName(self, name):
        self.gamename = name
        
        util.settings.beginGroup("fa.games")
        util.settings.setValue("gamename", self.gamename)        
        util.settings.endGroup()        
                
                
    def loadGameName(self):
        util.settings.beginGroup("fa.games")
        self.gamename = util.settings.value("gamename", None)        
        util.settings.endGroup()        
                
        #Default Game Name ...
        if not self.gamename:
            if (self.client.login):
                self.gamename = self.client.login + "'s game"
            else:
                self.gamename = "nobody's game"
        
