from PyQt5 import QtCore, QtWidgets, QtWebEngineWidgets
import util
from stats import mapstat
from config import Settings
import client
from util.qt import injectWebviewCSS
import time

from .leaderboard_widget import LeaderboardWidget
from api.stats_api import LeaderboardApiConnector
from ui.busy_widget import BusyWidget

import logging
logger = logging.getLogger(__name__)

ANTIFLOOD = 0.1

FormClass, BaseClass = util.THEME.loadUiType("stats/stats.ui")


class StatsWidget(BaseClass, FormClass, BusyWidget):

    # signals
    laddermaplist = QtCore.pyqtSignal(dict)
    laddermapstat = QtCore.pyqtSignal(dict)

    def __init__(self, client):
        super(BaseClass, self).__init__()

        self.setupUi(self)

        self.client = client
        
        self.client.lobby_info.statsInfo.connect(self.processStatsInfos)

        self.webview = QtWebEngineWidgets.QWebEngineView()
        self.webpage = WebEnginePage()
        
        self.websiteTab.layout().addWidget(self.webview)
        
        self.selected_player = None
        self.selected_player_loaded = False
        self.webview.loadFinished.connect(self.webview.show)
        self.leagues.currentChanged.connect(self.leagueUpdate)
        self.currentChanged.connect(self.busy_entered)
        self.pagesDivisions = {}
        self.pagesDivisionsResults = {}
        self.pagesAllLeagues = {}
        
        self.floodtimer = time.time()
        
        self.currentLeague = 0
        self.currentDivision = 0
        
        self.FORMATTER_LADDER        = str(util.THEME.readfile("stats/formatters/ladder.qthtml"))
        self.FORMATTER_LADDER_HEADER = str(util.THEME.readfile("stats/formatters/ladder_header.qthtml"))

        util.THEME.stylesheets_reloaded.connect(self.load_stylesheet)
        self.load_stylesheet()
    
        # setup other tabs
        self.mapstat = mapstat.LadderMapStat(self.client, self)

        self.webpage.setUrl(QtCore.QUrl("https://faforever.com/competitive/leaderboards/1v1"))
        self.webview.setPage(self.webpage)

        self.apiConnector = LeaderboardApiConnector(self.client.lobby_dispatch)
        self.apiConnector.requestData(dict(sort="id"))

        # hiding some non-functional tabs
        self.removeTab(self.indexOf(self.ladderTab))
        self.removeTab(self.indexOf(self.laddermapTab))

    def load_stylesheet(self):
        self.setStyleSheet(util.THEME.readstylesheet("stats/formatters/style.css"))

    @QtCore.pyqtSlot(int)
    def leagueUpdate(self, index):
        self.currentLeague = index + 1
        leagueTab = self.leagues.widget(index).findChild(QtWidgets.QTabWidget,"league"+str(index))
        if leagueTab:
            if leagueTab.currentIndex() == 0:
                if time.time() - self.floodtimer > ANTIFLOOD:
                    self.floodtimer = time.time() 
                    self.client.statsServer.send(dict(command="stats", type="league_table", league=self.currentLeague))

    @QtCore.pyqtSlot(int)
    def divisionsUpdate(self, index):
        if index == 0:
            if time.time() - self.floodtimer > ANTIFLOOD:
                self.floodtimer = time.time()
                self.client.statsServer.send(dict(command="stats", type="league_table", league=self.currentLeague))
        
        elif index == 1:
            tab = self.currentLeague - 1
            if tab not in self.pagesDivisions:
                    self.client.statsServer.send(dict(command="stats", type="divisions", league=self.currentLeague))
        
    @QtCore.pyqtSlot(int)
    def divisionUpdate(self, index):
        if time.time() - self.floodtimer > ANTIFLOOD:
            self.floodtimer = time.time()
            self.client.statsServer.send(dict(command="stats", type="division_table",
                                              league=self.currentLeague, division=index))
        
    def createDivisionsTabs(self, divisions):
        userDivision = ""
        me = self.client.me.player
        if me.league is not None:  # was me.division, but no there there
            userDivision = me.league[1]  # ? [0]=league and [1]=division
       
        pages = QtWidgets.QTabWidget()

        foundDivision = False
        
        for division in divisions:
            name = division["division"]
            index = division["number"]
            league = division["league"]
            widget = QtWidgets.QTextBrowser()
            
            if league not in self.pagesDivisionsResults:
                self.pagesDivisionsResults[league] = {}
            
            self.pagesDivisionsResults[league][index] = widget 
            
            pages.insertTab(index, widget, name)
            
            if name == userDivision:
                foundDivision = True
                pages.setCurrentIndex(index)
                self.client.statsServer.send(dict(command="stats", type="division_table", league=league, division=index))
        
        if not foundDivision:
            self.client.statsServer.send(dict(command="stats", type="division_table", league=league, division=0))
        
        pages.currentChanged.connect(self.divisionUpdate)
        return pages

    def createResults(self, values, table):
        
        formatter = self.FORMATTER_LADDER
        formatter_header = self.FORMATTER_LADDER_HEADER
        glist = []
        append = glist.append
        append("<table style='color:#3D3D3D' cellspacing='0' cellpadding='4' width='100%' height='100%'><tbody>")
        append(formatter_header.format(rank="rank", name="name", score="score", color="#92C1E4"))

        for val in values:
            rank = val["rank"]
            name = val["name"]
            score = str(val["score"])
            if self.client.login == name:
                append(formatter.format(rank=str(rank), name=name, score=score, color="#6CF"))
            elif rank % 2 == 0:
                append(formatter.format(rank=str(rank), name=name, score=str(val["score"]), color="#F1F1F1"))
            else:
                append(formatter.format(rank=str(rank), name=name, score=str(val["score"]), color="#D8D8D8"))

        append("</tbody></table>")
        html = "".join(glist)

        table.setHtml(html)
        
        table.verticalScrollBar().setValue(table.verticalScrollBar().minimum())
        return table

    @QtCore.pyqtSlot(int)
    def leaderboardsTabChanged(self, curr):
        self.leaderboards.widget(curr).entered()

    @QtCore.pyqtSlot(dict)
    def processStatsInfos(self, message):

        typeStat = message["type"]
        if typeStat == "divisions":
            self.currentLeague = message["league"]
            tab = self.currentLeague - 1

            if tab not in self.pagesDivisions:
                self.pagesDivisions[tab] = self.createDivisionsTabs(message["values"])
                leagueTab = self.leagues.widget(tab).findChild(QtWidgets.QTabWidget,"league"+str(tab))
                leagueTab.widget(1).layout().addWidget(self.pagesDivisions[tab])

        elif typeStat == "division_table":
            self.currentLeague = message["league"]
            self.currentDivision = message["division"]

            if self.currentLeague in self.pagesDivisionsResults:
                if self.currentDivision in self.pagesDivisionsResults[self.currentLeague]:
                    self.createResults(message["values"], self.pagesDivisionsResults[self.currentLeague][self.currentDivision])
                    
        elif typeStat == "league_table":
            self.currentLeague = message["league"]
            tab = self.currentLeague - 1
            if tab not in self.pagesAllLeagues:
                table = QtWidgets.QTextBrowser()
                self.pagesAllLeagues[tab] = self.createResults(message["values"], table)
                leagueTab = self.leagues.widget(tab).findChild(QtWidgets.QTabWidget,"league"+str(tab))
                leagueTab.currentChanged.connect(self.divisionsUpdate)
                leagueTab.widget(0).layout().addWidget(self.pagesAllLeagues[tab])

        elif typeStat == "ladder_map_stat":
            self.laddermapstat.emit(message)

        elif typeStat == "leaderboard":
            self.leaderboardNames = []
            for value in message["values"]:
                self.leaderboardNames.append(value["technicalName"])
            for i in range(len(self.leaderboardNames)):
                self.leaderboards.insertTab(i, 
                                            LeaderboardWidget(self.client, self, self.leaderboardNames[i]),
                                            self.leaderboardNames[i].capitalize().replace("_", " ")
                )
                self.client.replays.leaderboardList.addItem(self.leaderboardNames[i])

            self.leaderboards.setCurrentIndex(1)
            self.leaderboards.currentChanged.connect(self.leaderboardsTabChanged)

    def _injectCSS(self):
        if util.THEME.themeurl("ladder/style.css"):
            injectWebviewCSS(self.webview.page(), util.THEME.readstylesheet("ladder/style.css"))

    @QtCore.pyqtSlot()
    def busy_entered(self):
        if self.currentIndex() == self.indexOf(self.leaderboardsTab):
            self.leaderboards.currentChanged.emit(self.leaderboards.currentIndex())

class WebEnginePage(QtWebEngineWidgets.QWebEnginePage):
    def __init__(self):
        super().__init__()
        self.valid_urls = [
                           QtCore.QUrl("https://faforever.com/competitive/leaderboards/1v1")
                          ,QtCore.QUrl("https://faforever.com/competitive/leaderboards/global")
                          ,QtCore.QUrl("https://faforever.com/competitive/leaderboards/leagues")
                          ,QtCore.QUrl("https://faforever.com/competitive/tournaments")
        ]

    def acceptNavigationRequest(self, url, type, isMainFrame):
        if url in self.valid_urls or url.url()[:22] == "https://challonge.com/":
            return True
        else:
            return False
