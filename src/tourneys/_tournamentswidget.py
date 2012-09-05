from PyQt4 import QtCore, QtGui, Qt
import util

from tourneys import logger
from tourneys.swisstourneyitem import SwissTourneyItem, SwissTourneyItemDelegate
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
        
        self.tourneyList.setItemDelegate(SwissTourneyItemDelegate(self))
        
        self.tourneyList.itemDoubleClicked.connect(self.tourneyDoubleClicked)
        self.tourneyList.itemPressed.connect(self.tourneyPressed)
                
        self.client.tourneyTypesInfo.connect(self.processTourneyTypeInfo)
        self.client.tourneyInfo.connect(self.processTourneyInfo)
        
        self.tourneyTypeList.itemDoubleClicked.connect(self.hostTourneyClicked)
        
        
        self.title = ""
        self.description = ""
        self.minplayers = 2
        self.maxplayers = 99
        
        self.minrating = 0
        self.maxrating = 3000


    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def tourneyPressed(self, item):
        if QtGui.QApplication.mouseButtons() == QtCore.Qt.RightButton:            
            #Look up the associated chatter object        
            item.pressed(item)

    @QtCore.pyqtSlot(dict)
    def processTourneyInfo(self, message):
        '''
        Slot that interprets and propagates tourney_info messages into TourneyItems 
        '''
        uid = message["uid"]


        if uid not in self.tourneys:
            self.tourneys[uid] = SwissTourneyItem(self, uid)
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
        
    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def tourneyDoubleClicked(self, item):
        '''
        Slot that attempts to join or leave a tournament.
        ''' 
        if not self.client.login in item.players :
            
            self.client.send(dict(command="tournament", action = "join", uid=item.uid, type = item.type))
        else :
            self.client.send(dict(command="tournament", action = "leave", uid=item.uid, type = item.type))
        
        
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
          
        hosttourneywidget = HostTourneyWidget(self, item)
        
        if hosttourneywidget.exec_() == 1 :
            if self.tourneyname:
                self.client.send(dict(command="create_tournament", type = item.tourney, name=self.tourneyname, min_players = self.minplayers, max_players = self.maxplayers, min_rating = self.minrating, max_rating = self.maxrating, description = self.description))
