from PyQt5 import QtCore, QtGui, QtWidgets
import fa
from fa.replay import replay
import util

from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest

from coop.coopmapitem import CoopMapItem, CoopMapItemDelegate
from coop.coopmodel import CoopGameFilterModel
from ui.busy_widget import BusyWidget
import os

import logging
logger = logging.getLogger(__name__)

FormClass, BaseClass = util.THEME.loadUiType("coop/coop.ui")


class CoopWidget(FormClass, BaseClass, BusyWidget):
    def __init__(self, client, game_model, me,
                 gameview_builder, game_launcher):

        BaseClass.__init__(self)

        self.setupUi(self)

        self.client = client  # type: ClientWindow
        self._me = me
        self._game_model = CoopGameFilterModel(self._me, game_model)
        self._game_launcher = game_launcher
        self._gameview_builder = gameview_builder

        # Ranked search UI
        self.ispassworded = False
        self.loaded = False

        self.coop = {}
        self.cooptypes = {}

        self.options = []

        self.client.lobby_info.coopInfo.connect(self.processCoopInfo)

        self.coopList.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.coopList.setItemDelegate(CoopMapItemDelegate(self))

        self.gameview = self._gameview_builder(self._game_model, self.gameList)
        self.gameview.game_double_clicked.connect(self.gameDoubleClicked)

        self.coopList.itemDoubleClicked.connect(self.coopListDoubleClicked)
        self.coopList.itemClicked.connect(self.coopListClicked)

        self.client.lobby_info.coopLeaderBoard.connect(self.processLeaderBoardInfos)
        self.tabLeaderWidget.currentChanged.connect(self.askLeaderBoard)

        self.leaderBoard.setVisible(0)
        self.FORMATTER_LADDER        = str(util.THEME.readfile("coop/formatters/ladder.qthtml"))
        self.FORMATTER_LADDER_HEADER = str(util.THEME.readfile("coop/formatters/ladder_header.qthtml"))

        util.THEME.stylesheets_reloaded.connect(self.load_stylesheet)
        self.load_stylesheet()

        self.leaderBoardTextGeneral.anchorClicked.connect(self.openUrl)
        self.leaderBoardTextOne.anchorClicked.connect(self.openUrl)
        self.leaderBoardTextTwo.anchorClicked.connect(self.openUrl)
        self.leaderBoardTextThree.anchorClicked.connect(self.openUrl)
        self.leaderBoardTextFour.anchorClicked.connect(self.openUrl)

        self.replayDownload = QNetworkAccessManager()
        self.replayDownload.finished.connect(self.finishRequest)

        self.selectedItem = None

    def load_stylesheet(self):
        self.setStyleSheet(util.THEME.readstylesheet("coop/formatters/style.css"))

    def _addExistingGames(self, gameset):
        for game in gameset.values():
            self._addGame(game)

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
        """ Process leaderboard"""

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
        doc.addResource(3, QtCore.QUrl("style.css"), self.leaderBoard.styleSheet())
        html = "<html><head><link rel='stylesheet' type='text/css' href='style.css'></head><body>"

        if self.selectedItem:
            html += '<p class="division" align="center">'+self.selectedItem.name+'</p><hr/>'
        html += "<table class='players' cellspacing='0' cellpadding='0' width='630' height='100%'>"

        formatter = self.FORMATTER_LADDER
        formatter_header = self.FORMATTER_LADDER_HEADER
        cursor = w.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        w.setTextCursor(cursor) 
        color = "lime"
        line = formatter_header.format(rank="rank", names="names", time="time", color=color)
        html += line
        rank = 1
        for val in values:
            # val = values[uid]
            players = ", ".join(val["players"]) 
            numPlayers = str(len(val["players"]))
            timing = val["time"]
            gameuid = str(val["gameuid"])
            if val["secondary"] == 1:
                secondary = "Yes"
            else:
                secondary = "No"
            if rank % 2 == 0:
                line = formatter.format(rank=str(rank), numplayers=numPlayers, gameuid=gameuid, players=players,
                                        objectives=secondary, timing=timing, type="even")
            else:
                line = formatter.format(rank=str(rank), numplayers=numPlayers, gameuid=gameuid, players=players,
                                        objectives=secondary, timing=timing, type="")

            rank = rank + 1

            html += line

        html += "</tbody></table></body></html>"

        doc.setHtml(html)
        w.setDocument(doc)

        self.leaderBoard.setVisible(True)

    def busy_entered(self):
        if not self.loaded:
            self.client.lobby_connection.send(dict(command="coop_list"))
            self.loaded = True

    def askLeaderBoard(self):
        """
        ask the server for stats
        """
        if self.selectedItem:
            self.client.statsServer.send(dict(command="coop_stats", mission=self.selectedItem.uid,
                                              type=self.tabLeaderWidget.currentIndex()))

    def coopListClicked(self, item):
        """
        Hosting a coop event
        """
        if not hasattr(item, "mapUrl"):
            if item.isExpanded():
                item.setExpanded(False)
            else:
                item.setExpanded(True)
            return

        if item != self.selectedItem: 
            self.selectedItem = item
            self.client.statsServer.send(dict(command="coop_stats", mission=item.uid,
                                              type=self.tabLeaderWidget.currentIndex()))

    def coopListDoubleClicked(self, item):
        """
        Hosting a coop event
        """
        if not hasattr(item, "mapUrl"):
            return
        mapname = fa.maps.link2name(item.mapUrl)

        if not fa.instance.available():
            return

        self.client.games.stopSearchRanked()

        if not fa.check.check("coop"):
            return

        self._game_launcher.host_game(item.name, item.mod, mapname)

    @QtCore.pyqtSlot(dict)
    def processCoopInfo(self, message): 
        """
        Slot that interprets and propagates coop_info messages into the coop list 
        """
        uid = message["uid"]

        if uid not in self.coop:
            typeCoop = message["type"]

            if typeCoop not in self.cooptypes:
                root_item = QtWidgets.QTreeWidgetItem()
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

    def gameDoubleClicked(self, game):
        """
        Slot that attempts to join a game.
        """
        if not fa.instance.available():
            return

        if not fa.check.check(game.featured_mod, game.mapname, None, game.sim_mods):
            return

        if game.password_protected:
            passw, ok = QtWidgets.QInputDialog.getText(self.client, "Passworded game", "Enter password :",
                                                       QtWidgets.QLineEdit.Normal, "")
            if ok:
                self.client.join_game(uid=game.uid, password=passw)
        else:
            self.client.join_game(uid=game.uid)
