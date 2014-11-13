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





from PyQt4 import QtCore, QtGui, QtWebKit
import util
from stats import mapstat
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

        self.client.net.statsInfo.connect(self.processStatsInfos)

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

        self.FORMATTER_LADDER = unicode(util.readfile("stats/formatters/ladder.qthtml"))
        self.FORMATTER_LADDER_HEADER = unicode(util.readfile("stats/formatters/ladder_header.qthtml"))
        self.stylesheet = util.readstylesheet("stats/formatters/style.css")

        self.leagues.setStyleSheet(self.stylesheet)


        # setup other tabs
        self.mapstat = mapstat.LadderMapStat(self.client, self)



    @QtCore.pyqtSlot(int)
    def leagueUpdate(self, index):
        self.currentLeague = index + 1
        leagueTab = self.leagues.widget(index).findChild(QtGui.QTabWidget, "league" + str(index))
        if leagueTab :
            if leagueTab.currentIndex() == 0 :
                if time.time() - self.floodtimer > ANTIFLOOD :
                    self.floodtimer = time.time()
                    self.client.statsServer.send(dict(command="stats", type="league_table", league=self.currentLeague))

    @QtCore.pyqtSlot(int)
    def divisionsUpdate(self, index):
        if index == 0 :
            if time.time() - self.floodtimer > ANTIFLOOD :
                self.floodtimer = time.time()
                self.client.statsServer.send(dict(command="stats", type="league_table", league=self.currentLeague))

        elif index == 1 :
            tab = self.currentLeague - 1
            if not tab in self.pagesDivisions :
                    self.client.statsServer.send(dict(command="stats", type="divisions", league=self.currentLeague))

    @QtCore.pyqtSlot(int)
    def divisionUpdate(self, index):
        if time.time() - self.floodtimer > ANTIFLOOD :
            self.floodtimer = time.time()
            self.client.statsServer.send(dict(command="stats", type="division_table", league=self.currentLeague, division=index))

    def createDivisionsTabs(self, divisions):
        userDivision = ""
        if  self.client.getUserLeague(self.client.login) :
            userDivision = self.client.getUserLeague(self.client.login)["division"]

        pages = QtGui.QTabWidget()

        foundDivision = False

        for division in divisions :
            name = division["division"]
            index = division["number"]
            league = division["league"]
            widget = QtGui.QTextBrowser()

            if not league in self.pagesDivisionsResults :
                self.pagesDivisionsResults[league] = {}

            self.pagesDivisionsResults[league][index] = widget

            pages.insertTab(index, widget, name)

            if name == userDivision :
                foundDivision = True
                pages.setCurrentIndex(index)
                self.client.statsServer.send(dict(command="stats", type="division_table", league=league, division=index))

        if foundDivision == False :
            self.client.statsServer.send(dict(command="stats", type="division_table", league=league, division=0))

        pages.currentChanged.connect(self.divisionUpdate)
        return pages


    def createResults(self, values, table):

        doc = QtGui.QTextDocument()
        doc.addResource(3, QtCore.QUrl("style.css"), self.stylesheet)
        html = ("<html><head><link rel='stylesheet' type='text/css' href='style.css'></head><body><table class='players' cellspacing='0' cellpadding='0' width='100%' height='100%'>")

        formatter = self.FORMATTER_LADDER
        formatter_header = self.FORMATTER_LADDER_HEADER
        cursor = table.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        table.setTextCursor(cursor)
        color = "lime"
        line = formatter_header.format(rank="rank", name="name", score="score", color=color)
        html += line

        for val in values :
            rank = val["rank"]
            name = val["name"]
            if self.client.login == name :
                line = formatter.format(rank=str(rank), name=name, score=str(val["score"]), type="highlight")
            elif rank % 2 == 0 :
                line = formatter.format(rank=str(rank), name=name, score=str(val["score"]), type="even")
            else :
                line = formatter.format(rank=str(rank), name=name, score=str(val["score"]), type="")

            html += line

        html += "</tbody></table></body></html>"

        doc.setHtml(html)
        table.setDocument(doc)

        table.verticalScrollBar().setValue(table.verticalScrollBar().minimum())
        return table


    @QtCore.pyqtSlot(dict)
    def processStatsInfos(self, message):

        typeStat = message["type"]
        if typeStat == "divisions" :
            self.currentLeague = message["league"]
            tab = self.currentLeague - 1

            if not tab in self.pagesDivisions :
                print "no tab in division"
                self.pagesDivisions[tab] = self.createDivisionsTabs(message["values"])
                leagueTab = self.leagues.widget(tab).findChild(QtGui.QTabWidget, "league" + str(tab))
                leagueTab.widget(1).layout().addWidget(self.pagesDivisions[tab])
                print "done"


        elif typeStat == "division_table" :
            self.currentLeague = message["league"]
            self.currentDivision = message["division"]

            if self.currentLeague in self.pagesDivisionsResults :
                if self.currentDivision in self.pagesDivisionsResults[self.currentLeague] :
                    self.createResults(message["values"], self.pagesDivisionsResults[self.currentLeague][self.currentDivision])


        elif typeStat == "league_table" :
            self.currentLeague = message["league"]
            tab = self.currentLeague - 1
            if not tab in self.pagesAllLeagues :
                table = QtGui.QTextBrowser()
                self.pagesAllLeagues[tab] = self.createResults(message["values"], table)
                leagueTab = self.leagues.widget(tab).findChild(QtGui.QTabWidget, "league" + str(tab))
                leagueTab.currentChanged.connect(self.divisionsUpdate)
                leagueTab.widget(0).layout().addWidget(self.pagesAllLeagues[tab])

        elif typeStat == "ladder_maps" :
            self.laddermaplist.emit(message)

        elif typeStat == "ladder_map_stat" :
            self.laddermapstat.emit(message)

    @QtCore.pyqtSlot()
    def updating(self):

        self.client.statsServer.send(dict(command="stats", type="ladder_maps"))

        if  self.client.getUserLeague(self.client.login) :
            self.leagues.setCurrentIndex(self.client.getUserLeague(self.client.login)["league"] - 1)
        else :
            self.leagues.setCurrentIndex(0)
            self.client.statsServer.send(dict(command="stats", type="league_table", league=1))

        if (self.loaded):
            return


        self.loaded = True

        self.webview.setVisible(False)

        # If a local theme CSS exists, skin the WebView with it
        if util.themeurl("ladder/style.css"):
            self.webview.settings().setUserStyleSheetUrl(util.themeurl("ladder/style.css"))

        self.webview.setUrl(QtCore.QUrl("http://content.faforever.com/faf/leaderboards/read-leader.php?board=1v1&username=%s" % (self.client.login)))



