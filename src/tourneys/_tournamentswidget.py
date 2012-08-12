from PyQt4 import QtCore, QtGui
import util

from tourneys import logger
from tourneys.tourneyitem import TourneyItem, TourneyItemDelegate
from tourneys.tourneytypeitem import TourneyTypeItem
from tourneys.hosttourneywidget import HostTourneyWidget
import fa

FormClass, BaseClass = util.loadUiType("tournaments/tournaments.ui")



class TournamentsWidget(FormClass, BaseClass):
    def __init__(self, client, *args, **kwargs):
        
        BaseClass.__init__(self, *args, **kwargs)        
        
        self.setupUi(self)

        self.client = client
        self.client.tourneyTab.layout().addWidget(self)
        
        #Dictionary containing our actual tournaments.
        self.tourneys = {}
        
        self.tourneyList.setItemDelegate(TourneyItemDelegate(self))
        
        self.client.tourneyTypesInfo.connect(self.processTourneyTypeInfo)
        self.client.tourneyInfo.connect(self.processTourneyInfo)
        
        self.tourneyTypeList.itemDoubleClicked.connect(self.hostTourneyClicked)
        
        self.loadTourneyName()

    @QtCore.pyqtSlot(dict)
    def processTourneyInfo(self, message):
        '''
        Slot that interprets and propagates tourney_info messages into TourneyItems 
        '''
        uid = message["uid"]

        print message
        if uid not in self.tourneys:
            self.tourneys[uid] = TourneyItem(uid)
            self.tourneyList.addItem(self.tourneys[uid])
            self.tourneys[uid].update(message, self.client)
        else:
            self.tourneys[uid].update(message, self.client)


        #Special case: removal of a game that has ended         
        if message['state'] == "closed":
            if uid in self.games:
                self.gameList.takeItem(self.gameList.row(self.games[uid]))
                del self.games[uid]    
            return
        
    @QtCore.pyqtSlot(dict)
    def processTourneyTypeInfo(self, message):
        '''
        Slot that interprets and propagates tourney type info messages into the tourney type list 
        ''' 
        
        item = TourneyTypeItem(message)
        self.tourneyTypeList.addItem(item)       


    
    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def hostTourneyClicked(self, item):
        '''
        Hosting a tournament event
        '''
        if not fa.exe.available():
            return

        # A simple Hosting dialog.
        if fa.exe.check(item.mod):     
            hosttourneywidget = HostTourneyWidget(self, item)
            
            if hosttourneywidget.exec_() == 1 :
                if self.tourneyname:
                    self.client.send(dict(command="create_tournament", type = item.tourney, name=self.tourneyname, min_players = 2, max_players = 13))

    def saveTourneyName(self, name):
        self.tourneyname = name
        
        util.settings.beginGroup("fa.tournaments")
        util.settings.setValue("tourneyname", self.tourneyname)        
        util.settings.endGroup()        
                
                
    def loadTourneyName(self):
        util.settings.beginGroup("fa.tournaments")
        self.tourneyname = util.settings.value("tourneyname", None)        
        util.settings.endGroup()        
                
        #Default tourney Name ...
        if not self.tourneyname:
            if (self.client.login):
                self.tourneyname = self.client.login + "'s tournament"
            else:
                self.tourneyname = "nobody's tournament"