from PyQt4 import QtCore, QtGui, QtWebKit
import util
from stats import logger
import client
import json


FormClass, BaseClass = util.loadUiType("stats/stats.ui")

class StatsWidget(BaseClass, FormClass):
    def __init__(self, client):
        super(BaseClass, self).__init__()

        self.setupUi(self)

        self.client = client
        client.ladderTab.layout().addWidget(self)
        
        self.client.statsInfo.connect(self.processStatsInfos)

        self.client = client

        self.webview = QtWebKit.QWebView()
        
        self.globalTab.layout().addWidget(self.webview)
        
        self.loaded = False
        self.client.showLadder.connect(self.updating)
        self.webview.loadFinished.connect(self.webview.show)
        self.leagues.currentChanged.connect(self.leagueUpdate)
        self.pages = {}
        self.pagesAllLeagues = {}
    
    @QtCore.pyqtSlot(int)
    def leagueUpdate(self, index):
        
        leagueTab = self.leagues.widget(index).findChild(QtGui.QTabWidget,"league"+str(index))
        if leagueTab :
            if leagueTab.currentIndex() == 0 :
                self.client.send(dict(command="stats", type="league_table", league=index+1))
                
        
        
    def createDivisionsTabs(self, divisions):
        userDivision = ""
        if  self.client.getUserLeague(self.client.login) :
            userDivision = self.client.getUserLeague(self.client.login)["division"]
       
        pages = QtGui.QTabWidget()
        for division in divisions :
            name = division["division"]
            index = division["number"]
            widget = QtGui.QListView()
            pages.insertTab(index, widget, name)
            if name == userDivision :
                pages.setCurrentIndex(index)
                league = division["league"]
                self.client.send(dict(command="stats", type="division_table", league=league, division=division))
            
            
        return pages
            
    
    def createResultLeague(self, values):
        table = QtGui.QTableWidget(len(values), 3)
        table.verticalHeader().setVisible(0)
        table.setSelectionMode(0)
        table.setHorizontalHeaderItem(0, QtGui.QTableWidgetItem("Rank"))
        table.setHorizontalHeaderItem(1, QtGui.QTableWidgetItem("Name"))
        table.setHorizontalHeaderItem(2, QtGui.QTableWidgetItem("Score"))
        
        for val in values :
            table.setItem(val["rank"]-1, 0, QtGui.QTableWidgetItem(str(val["rank"])))
            table.setItem(val["rank"]-1, 1, QtGui.QTableWidgetItem(val["name"]))
            table.setItem(val["rank"]-1, 2, QtGui.QTableWidgetItem(str(val["score"])))
        return table
        
    
    @QtCore.pyqtSlot(dict)
    def processStatsInfos(self, message):

        type = message["type"]
        if type == "divisions" :
#            tab = message["league"]-1
#            if not tab in self.pages :
#                self.pages[tab] = self.createDivisionsTabs(message["values"])
#                leaguesTabs = self.leagues.widget(tab)
#                leaguesTabs.widget(1).layout().addWidget(self.pages[tab])
            pass
        if type == "division_table" :
            print message
        if type == "league_table" :
            league = message["league"]
            tab = league-1
            if not tab in self.pagesAllLeagues :
                self.pagesAllLeagues[tab] = self.createResultLeague(message["values"])
                leagueTab = self.leagues.widget(tab).findChild(QtGui.QTabWidget,"league"+str(tab))
                leagueTab.widget(0).layout().addWidget(self.pagesAllLeagues[tab])
            
            

    
    @QtCore.pyqtSlot()
    def updating(self):
    
        if  self.client.getUserLeague(self.client.login) :
            self.leagues.setCurrentIndex(self.client.getUserLeague(self.client.login)["league"]-1)
        else :
            self.leagues.setCurrentIndex(0)
        
        if (self.loaded): 
            return 
        
        self.client.send(dict(command="stats", type="league_table", league=1))   
 
        self.loaded = True
        
        self.webview.setVisible(False)

        #If a local theme CSS exists, skin the WebView with it
        if util.themeurl("ladder/style.css"):
            self.webview.settings().setUserStyleSheetUrl(util.themeurl("ladder/style.css"))

        self.webview.setUrl(QtCore.QUrl("http://faforever.com/faf/leaderboards/read-leader.php?board=global&username=%s" % (self.client.login)))
        
        
    
