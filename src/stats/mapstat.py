import util
from PyQt4 import QtGui, QtCore
import json
import datetime
from fa import maps

FormClass, BaseClass = util.loadUiType("stats/mapstat.ui")

class LadderMapStat(FormClass, BaseClass):
    '''
    This class list all the maps given by the server, and ask for more details when selected.
    '''
    def __init__(self, client, parent, *args, **kwargs):
        FormClass.__init__(self, client, *args, **kwargs)
        BaseClass.__init__(self, client, *args, **kwargs)

        self.setupUi(self)
        
        self.parent = parent
        self.client = client
        
        # adding ourself to the stat tab
                #add self to client's window
        self.parent.laddermapTab.layout().addWidget(self)

        self.parent.laddermaplist.connect(self.updatemaps)
        self.parent.laddermapstat.connect(self.updatemapstat)
        
        
        self.maplist.itemClicked.connect(self.mapselected)
        
    def getSeasonDate(self):
        now = datetime.date.today()

        if (now.month == 3 and now.day < 21) or now.month < 3 :
            previous = datetime.datetime(now.year-1, 12, 21)
            
        elif (now.month == 6 and now.day < 21) or now.month < 6 :
    
            previous = datetime.datetime(now.year, 03, 21)
            
        elif (now.month == 9 and now.day < 21) or now.month < 9 :
         
            previous = datetime.datetime(now.year, 06, 21)
            
        else  :
          
            previous = datetime.datetime(now.year, 12, 21)
        
        return previous.strftime('%d %B %Y')
    
    @QtCore.pyqtSlot(dict)
    def updatemapstat(self, message):
        ''' fill all the datas for that map'''

        values = message["values"]
       
        draws = values["draws"]
        
        uef_total = values["uef_total"]
        uef_win = values["uef_win"]
        
        cybran_total = values["cybran_total"]
        cybran_win = values["cybran_win"]
        
        aeon_total = values["aeon_total"]
        aeon_win = values["aeon_win"]
        
        sera_total = values["sera_total"]
        sera_win = values["sera_win"]
        
        duration_max = values["duration_max"]
        duration_min = values["duration_min"]
        duration_avg = values["duration_avg"]
        
        game_played = values["game_played"]
        
        self.mapstats.insertHtml("<br><font size='+1'>"+str(game_played)+" games played on this map </font><br>")
        
        self.mapstats.insertHtml("<br><font size='+1'>"+str(round(float(draws)/float(game_played),2))+" of the games end with a draw ("+str(draws)+" games) </font><br>")

        
        
        
        totalFaction = float(uef_total + cybran_total + aeon_total + sera_total) 
        
        percentUef      = round((uef_total     /  totalFaction) * 100.0, 2)
        
        print totalFaction 
        percentAeon     = round((aeon_total    /  totalFaction) * 100.0, 2)
        percentCybran   = round((cybran_total  /  totalFaction) * 100.0, 2)
        percentSera     = round((sera_total    /  totalFaction) * 100.0, 2)
        
        self.mapstats.insertHtml("<br><font size='+1'>"+str(percentUef)+" % UEF ( in "+str(uef_total)+" games) </font>")
        self.mapstats.insertHtml("<br><font size='+1'>"+str(percentCybran)+" % Cybran ( in "+str(cybran_total)+" games) </font>")
        self.mapstats.insertHtml("<br><font size='+1'>"+str(percentAeon)+" % Aeon ( in "+str(aeon_total)+" games) </font>")      
        self.mapstats.insertHtml("<br><font size='+1'>"+str(percentSera)+" % Seraphim ( in "+str(sera_total)+" games) </font><br>")

        
        percentwinUef      = round((uef_win     /  float(uef_total)) * 100.0, 2)
        percentwinAeon     = round((aeon_win    /  float(aeon_total)) * 100.0, 2)
        percentwinCybran   = round((cybran_win  /  float(cybran_total)) * 100.0, 2)
        percentwinSera     = round((sera_win    /  float(sera_total)) * 100.0, 2)
        
        self.mapstats.insertHtml("<br><font size='+1'>Win ratios : </font>")
        self.mapstats.insertHtml("<br><font size='+1'>UEF : "+str(percentwinUef)+ " % ("+str(uef_win)+" games won)</font>")
        self.mapstats.insertHtml("<br><font size='+1'>Cybran : "+str(percentwinCybran)+ " % ("+str(cybran_win)+" games won)</font>")
        self.mapstats.insertHtml("<br><font size='+1'>Aeon : "+str(percentwinAeon)+ " % ("+str(aeon_win)+" games won)</font>")
        self.mapstats.insertHtml("<br><font size='+1'>Seraphim : "+str(percentwinSera)+ " % ("+str(sera_win)+" games won)</font>")


    
    def mapselected(self, item):
        ''' user has selected a map, we send the request to the server'''
        
        mapid = item.data(32)[0]
        self.client.send(dict(command="stats", type="ladder_map_stat", mapid = mapid))
        self.mapstats.clear()
        
        realmap = item.data(32)[1].split("/")[1].strip(".zip")
        print realmap

        self.mapstats.document().addResource(QtGui.QTextDocument.ImageResource,  QtCore.QUrl("map.png"), maps.preview(realmap, True))

        self.mapstats.insertHtml("<img src=\"map.png\" /><br><font size='+5'>" + item.text() + "</font><br><br>")
        
        
    @QtCore.pyqtSlot(dict)
    def updatemaps(self, message):

        self.maps = message["values"]
        
        
        self.mapstats.insertHtml("<font size='+5'>Stats since : %s</font>" % self.getSeasonDate() )
        self.mapstats.insertHtml("<font size='+1'><br>Number of game played :</font><font size='+1' color = 'red'> %i </font>" % message["gamesplayed"] )
        
        #clearing current map list
        self.maplist.clear()
        
        for mp in self.maps :
            mapid = mp["idmap"]
            name  = mp["mapname"]
            realname = mp["maprealname"]
            
            item = QtGui.QListWidgetItem (name)
            item.setData(32, (mapid, realname))
            self.maplist.addItem(item)
            
        self.maplist.sortItems(0)
        
        
        