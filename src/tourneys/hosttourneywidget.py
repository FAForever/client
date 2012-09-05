from PyQt4 import QtCore, QtGui
import util

FormClass, BaseClass = util.loadUiType("tournaments/host.ui")

class HostTourneyWidget(FormClass, BaseClass):
    def __init__(self, parent, item, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)       

        self.setupUi(self)
        self.parent = parent
        
       
        
        self.setStyleSheet(self.parent.client.styleSheet())
        
        self.setWindowTitle ( "Hosting Tournament")
        self.titleEdit.setText ( self.parent.title )
        self.descriptionText.setHtml( self.parent.description )
        self.minRating.setValue ( self.parent.minrating )
        self.maxRating.setValue ( self.parent.maxrating )
        self.minPlayers.setValue ( self.parent.minplayers )
        self.maxPlayers.setValue ( self.parent.maxplayers )
#        
        self.hostButton.released.connect(self.hosting)

    def hosting(self):
        
        self.parent.title = self.titleEdit.text().strip()
        self.parent.description = self.descriptionText.toPlainText ()
        
        self.parent.minrating = self.minRating.value()
        self.parent.maxrating = self.maxRating.value()
        
        self.parent.minplayers = self.minPlayers.value()
        self.parent.maxplayers = self.maxPlayers.value()
        
        self.done(1)
        