
from PyQt4 import QtCore, QtGui
import util
import secondaryServer

from tourneys.tourneyitem import TourneyItem, TourneyItemDelegate

from config import modules as cfg

FormClass, BaseClass = util.loadUiType("tournaments/tournaments.ui")


class TournamentsWidget(FormClass, BaseClass):
    ''' list and manage the main tournament lister '''
    
    def __init__(self, client, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)        
        
        self.setupUi(self)

        self.client = client
        self.client.tourneyTab.layout().addWidget(self)
        
        #tournament server
        self.tourneyServer = secondaryServer.SecondaryServer("Tournament", 11001, self)
        self.tourneyServer.setInvisible()

        #Dictionary containing our actual tournaments.
        self.tourneys = {}
  
        self.tourneyList.setItemDelegate(TourneyItemDelegate(self))
        
        self.tourneyList.itemDoubleClicked.connect(self.tourneyDoubleClicked)
        
        self.tourneysTab = {}

        #Special stylesheet       
        self.setStyleSheet(util.readstylesheet("tournaments/formatters/style.css"))

        self.updateTimer = QtCore.QTimer(self)
        self.updateTimer.timeout.connect(self.updateTournaments)
        self.updateTimer.start(600000)
        
    
    def showEvent(self, event):
        self.updateTournaments()
        return BaseClass.showEvent(self, event)

    def updateTournaments(self):
        self.tourneyServer.send(dict(command="get_tournaments"))
        
       
    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def tourneyDoubleClicked(self, item):
        '''
        Slot that attempts to join or leave a tournament.
        ''' 
        if not cfg.user.login.get() in item.playersname :
            reply = QtGui.QMessageBox.question(self.client, "Register",
                "Do you want to register to this tournament ?",
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:
                self.tourneyServer.send(dict(command="add_participant", uid=item.uid, login=cfg.user.login.get()))

        else :
            reply = QtGui.QMessageBox.question(self.client, "Register",
                "Do you want to leave this tournament ?",
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:   
                self.tourneyServer.send(dict(command="remove_participant", uid=item.uid, login=cfg.user.login.get())) 
    
                
    def handle_tournaments_info(self, message):
        #self.tourneyList.clear()
        tournaments = message["data"]
        for uid in tournaments :
            if not uid in self.tourneys :
                self.tourneys[uid] = TourneyItem(self, uid)
                self.tourneyList.addItem(self.tourneys[uid])
                self.tourneys[uid].update(tournaments[uid], self.client)
            else :
                self.tourneys[uid].update(tournaments[uid], self.client)
