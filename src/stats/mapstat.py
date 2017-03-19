

import util
from PyQt5 import QtWidgets, QtCore
import json
import datetime
from fa import maps

FormClass, BaseClass = util.loadUiType("stats/mapstat.ui")

class LadderMapStat(FormClass, BaseClass):
    """
    This class list all the maps given by the server, and ask for more details when selected.
    """
    def __init__(self, client, parent, *args, **kwargs):
        BaseClass.__init__(self, client, *args, **kwargs)

        self.setupUi(self)
        
        self.parent = parent
        self.client = client
        
        self.mapid = 0

        # adding ourself to the stat tab

        self.parent.laddermapTab.layout().addWidget(self)

        self.parent.laddermaplist.connect(self.updatemaps)
        self.parent.laddermapstat.connect(self.updatemapstat)

        self.maplist.itemClicked.connect(self.mapselected)
        
    def getSeasonDate(self):
        now = datetime.date.today()

        if (now.month == 3 and now.day < 21) or now.month < 3:
            previous = datetime.datetime(now.year-1, 12, 21)
            
        elif (now.month == 6 and now.day < 21) or now.month < 6:
    
            previous = datetime.datetime(now.year, 0o3, 21)
            
        elif (now.month == 9 and now.day < 21) or now.month < 9:
         
            previous = datetime.datetime(now.year, 0o6, 21)
            
        else:
          
            previous = datetime.datetime(now.year, 12, 21)
        
        return previous.strftime('%d %B %Y')
    
    @QtCore.pyqtSlot(dict)
    def updatemapstat(self, message):
        """ fill all the data for that map """

        if message["idmap"] != self.mapid :
            return

        values = message["values"]
       
        draws = values["draws"]
        
        uef_total = values["uef_total"]
        uef_win = values["uef_win"]
        uef_ignore = values["uef_ignore"]
        
        cybran_total = values["cybran_total"]
        cybran_win = values["cybran_win"]
        cybran_ignore = values["cybran_ignore"]
        
        aeon_total = values["aeon_total"]
        aeon_win = values["aeon_win"]
        aeon_ignore = values["aeon_ignore"]
        
        sera_total = values["sera_total"]
        sera_win = values["sera_win"]
        sera_ignore = values["sera_ignore"]
        
        duration_max = values["duration_max"]
        duration_avg = values["duration_avg"]
        
        avgm, avgs = divmod(duration_avg, 60)
        averagetime = "%02d minutes %02d seconds" % (avgm, avgs)

        maxm, maxs = divmod(duration_max, 60)
        maxtime = "%02d minutes %02d seconds" % (maxm, maxs)
        
        game_played = values["game_played"]
        
        if game_played == 0:
            game_played = 1

        self.mapstats.insertHtml("<br><font size='+1'>" + str(game_played) + " games played on this map </font><br>")
        
        self.mapstats.insertHtml("<br><font size='+1'>" + str(round(float(draws)/float(game_played),2)) +
                                 "% of the games end with a draw ("+str(draws) + " games) </font><br>")

        self.mapstats.insertHtml("<br><font size='+1'> Average time for a game : " + averagetime + "</font><br>")
        self.mapstats.insertHtml("<br><font size='+1'> Maximum time for a game : " + maxtime + "</font><br>")
        
        totalFaction = float(uef_total + cybran_total + aeon_total + sera_total) 
        if totalFaction == 0:
            totalFaction = 1
        
        percentUef    = round((uef_total    / totalFaction) * 100.0, 2)
        
        percentAeon   = round((aeon_total   / totalFaction) * 100.0, 2)
        percentCybran = round((cybran_total / totalFaction) * 100.0, 2)
        percentSera   = round((sera_total   / totalFaction) * 100.0, 2)
        
        self.mapstats.insertHtml("<br><font size='+1'>" + str(percentUef) + " % UEF ("+str(uef_total) + " occurrences) </font>")
        self.mapstats.insertHtml("<br><font size='+1'>" + str(percentCybran) + " % Cybran ("+str(cybran_total) + " occurrences) </font>")
        self.mapstats.insertHtml("<br><font size='+1'>" + str(percentAeon) + " % Aeon ("+str(aeon_total) + " occurrences) </font>")
        self.mapstats.insertHtml("<br><font size='+1'>" + str(percentSera) + " % Seraphim ("+str(sera_total) + " occurrences) </font><br>")

        # if a win was ignored, it's because of a mirror matchup. No win count, but we have to remove 2 times the occurences.
        # once for each player..
        
        uefnomirror = (float(uef_total) - float(uef_ignore) * 2)
        cybrannomirror = (float(cybran_total) - float(cybran_ignore) * 2)
        aeonnomirror = (float(aeon_total) - float(aeon_ignore) * 2)
        seranomirror = (float(sera_total) - float(sera_ignore) * 2)

        if uefnomirror == 0:
            uefnomirror = 1

        if cybrannomirror == 0:
            cybrannomirror = 1

        if aeonnomirror == 0:
            aeonnomirror = 1

        if seranomirror == 0:
            seranomirror = 1
        
        percentwinUef    = round((uef_win    / uefnomirror) * 100.0, 2)
        percentwinCybran = round((cybran_win / cybrannomirror) * 100.0, 2)
        percentwinAeon   = round((aeon_win   / aeonnomirror) * 100.0, 2)
        percentwinSera   = round((sera_win   / seranomirror) * 100.0, 2)
        
        self.mapstats.insertHtml("<br><font size='+1'>Win ratios : </font>")
        self.mapstats.insertHtml("<br><font size='+1'>UEF : " + str(percentwinUef) + " % ("+str(uef_win) + " games won in "+str(int(uefnomirror)) + " no mirror matchup games)</font>")
        self.mapstats.insertHtml("<br><font size='+1'>Cybran : " + str(percentwinCybran) + " % ("+str(cybran_win) + " games won in " + str(int(cybrannomirror)) + " no mirror matchup games)</font>")
        self.mapstats.insertHtml("<br><font size='+1'>Aeon : " + str(percentwinAeon) + " % ("+str(aeon_win) + " games won in " + str(int(aeonnomirror)) + " no mirror matchup games)</font>")
        self.mapstats.insertHtml("<br><font size='+1'>Seraphim : " + str(percentwinSera) + " % ("+str(sera_win) + " games won in " + str(int(seranomirror)) + " no mirror matchup games)</font>")

    def mapselected(self, item):
        """ user has selected a map, we send the request to the server """
        
        self.mapstats.clear()
        self.mapid = item.data(32)[0]
        realmap = item.data(32)[1].split("/")[1][:-4]

        self.mapstats.document().addResource(QtGui.QTextDocument.ImageResource,  QtCore.QUrl("map.png"), maps.preview(realmap, True, force=True))

        self.mapstats.insertHtml("<img src=\"map.png\" /><br><font size='+5'>" + item.text() + "</font><br><br>")
        self.client.statsServer.send(dict(command="stats", type="ladder_map_stat", mapid=self.mapid))

    @QtCore.pyqtSlot(dict)
    def updatemaps(self, message):

        self.maps = message["values"]
        
        self.mapstats.insertHtml("<font size='+5'>Stats since : %s</font>" % self.getSeasonDate())
        self.mapstats.insertHtml("<font size='+1'><br>Number of game played :</font><font size='+1' color='red'> %i </font>" % message["gamesplayed"])
        
        # clearing current map list
        self.maplist.clear()
        
        for mp in self.maps:
            mapid = mp["idmap"]
            name = mp["mapname"]
            realname = mp["maprealname"]
            
            item = QtWidgets.QListWidgetItem(name)
            item.setData(32, (mapid, realname))
            self.maplist.addItem(item)
            
        self.maplist.sortItems(0)
