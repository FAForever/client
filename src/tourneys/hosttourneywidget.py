from PyQt4 import QtCore, QtGui
import util

FormClass, BaseClass = util.loadUiType("tournaments/host.ui")

class HostTourneyWidget(FormClass, BaseClass):
    def __init__(self, parent, item, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)       

        self.setupUi(self)
        self.parent = parent
        
       
        
        self.setStyleSheet(self.parent.client.styleSheet())
        
        self.setWindowTitle ( "Hosting Tournament : " + item.name )
        self.titleEdit.setText ( self.parent.tourneyname )

#        
        self.hostButton.released.connect(self.hosting)

    def hosting(self):
        self.parent.saveTourneyName(self.titleEdit.text().strip())
        self.parent.description = self.descriptionText.toPlainText ()
        
        self.parent.minrating = self.minRating.value()
        self.parent.maxrating = self.maxRating.value()
        
        self.parent.minplayers = self.minPlayers.value()
        self.parent.maxplayers = self.maxPlayers.value()
        
        self.done(1)