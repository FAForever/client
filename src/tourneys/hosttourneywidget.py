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
#        self.game = GameItem(0)
#        self.gamePreview.setItemDelegate(GameItemDelegate(self))
#        self.gamePreview.addItem(self.tournament)
#        
        self.hostButton.released.connect(self.hosting)
        self.titleEdit.textChanged.connect(self.updateText)

    def updateText(self, text):
        pass
        #self.message['title'] = text
        #self.game.update(self.message, self.parent.client)

    def hosting(self):
        self.parent.saveTourneyName(self.titleEdit.text().strip())
        self.done(1)