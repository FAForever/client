

from PyQt4 import QtCore, QtGui, QtWebKit
import util
from stats import mapstat
from config import Settings
import client
import time

import logging
logger = logging.getLogger(__name__)

ANTIFLOOD = 0.1

FormClass, BaseClass = util.loadUiType("stats/stats.ui")


class StatsWidget(BaseClass, FormClass):

    # signals
    laddermaplist = QtCore.pyqtSignal(dict)
    laddermapstat = QtCore.pyqtSignal(dict)

    def __init__(self, client):
        super(BaseClass, self).__init__()

        self.setupUi(self)

        self.client = client
        client.ladderTab.layout().addWidget(self)
        
        self.client.statsInfo.connect(self.processStatsInfos)

        self.client = client

        self.webview = QtWebKit.QWebView()
        
        self.LadderRatings.layout().addWidget(self.webview)
        
        self.loaded = False
        self.client.showLadder.connect(self.updating)
        self.webview.loadFinished.connect(self.webview.show)
        self.leagues.currentChanged.connect(self.leagueUpdate)
        self.pagesDivisions = {}
        self.pagesDivisionsResults = {}
        self.pagesAllLeagues = {}
        
        self.floodtimer = time.time()
        
        self.currentLeague = 0
        self.currentDivision = 0

        self.stylesheet = util.readstylesheet("stats/formatters/style.css")

        self.leagues.setStyleSheet(self.stylesheet)
    
        # setup other tabs
        self.mapstat = mapstat.LadderMapStat(self.client, self)

    @QtCore.pyqtSlot(int)
    def leagueUpdate(self, index):
        self.currentLeague = index + 1
        leagueTab = self.leagues.widget(index).findChild(QtGui.QTabWidget,"league"+str(index))
        if leagueTab:
            if leagueTab.currentIndex() == 0:
                if time.time() - self.floodtimer > ANTIFLOOD :
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
            self.client.statsServer.send(dict(command="stats", type="division_table", league=self.currentLeague, division=index))           
        
    def createDivisionsTabs(self, divisions):
        userDivision = ""
        me = self.client.me
        if me.division is not None:
            userDivision = me.division
       
        pages = QtGui.QTabWidget()

        foundDivision = False
        
        for division in divisions:
            name = division["division"]
            index = division["number"]
            league = division["league"]
            widget = QtGui.QTextBrowser()
            
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
        
        doc = QtGui.QTextDocument()
        doc.addResource(3, QtCore.QUrl("style.css"), self.stylesheet)

        cursor = table.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        table.setTextCursor(cursor)

        glist = []
        append = glist.append
        append("<html><head><link rel='stylesheet' type='text/css' href='style.css'></head><body>"
               "<table class='players' cellspacing='0' cellpadding='0' width='100%' height='100%'><tbody>"
               "<tr><th width='50'>rank</th><th width='100%'>name</th><th width='50'>score</th></tr>")

        for val in values:
            rank = val["rank"]
            name = val["name"]
            score = str(val["score"])
            if self.client.login == name:
                append("<tr class='%s'><td>%s</td><td>%s</td><td>%s</td></tr>" % ("highlight", str(rank), name, score))
            elif rank % 2 == 0:
                append("<tr class='%s'><td>%s</td><td>%s</td><td>%s</td></tr>" % ("even", str(rank), name, score))
            else:
                append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (str(rank), name, score))

        append("</tbody></table></body></html>")
        html = "".join(glist)

        doc.setHtml(html)
        table.setDocument(doc)
        
        table.verticalScrollBar().setValue(table.verticalScrollBar().minimum())
        return table

    @QtCore.pyqtSlot(dict)
    def processStatsInfos(self, message):

        typeStat = message["type"]
        if typeStat == "divisions":
            self.currentLeague = message["league"]
            tab = self.currentLeague - 1

            if tab not in self.pagesDivisions:
                self.pagesDivisions[tab] = self.createDivisionsTabs(message["values"])
                leagueTab = self.leagues.widget(tab).findChild(QtGui.QTabWidget,"league"+str(tab))   
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
                table = QtGui.QTextBrowser()
                self.pagesAllLeagues[tab] = self.createResults(message["values"], table)
                leagueTab = self.leagues.widget(tab).findChild(QtGui.QTabWidget,"league"+str(tab))
                leagueTab.currentChanged.connect(self.divisionsUpdate)
                leagueTab.widget(0).layout().addWidget(self.pagesAllLeagues[tab])

        elif typeStat == "ladder_map_stat":
            self.laddermapstat.emit(message)

    @QtCore.pyqtSlot()
    def updating(self):
        me = self.client.players[self.client.login]
        if me.league is not None:
            self.leagues.setCurrentIndex(me.league - 1)
        else:
            self.leagues.setCurrentIndex(5)  # currently useless -> 5 = direct to Ladder Ratings
            self.client.statsServer.send(dict(command="stats", type="league_table", league=1))

        if self.loaded:
            return

        self.loaded = True
        
        self.webview.setVisible(False)

        # If a local theme CSS exists, skin the WebView with it
        if util.themeurl("ladder/style.css"):
            self.webview.settings().setUserStyleSheetUrl(util.themeurl("ladder/style.css"))

        self.webview.setUrl(QtCore.QUrl("{}/faf/leaderboards/read-leader.php?board=1v1&username={}".format(Settings.get('content/host'), me.login)))
