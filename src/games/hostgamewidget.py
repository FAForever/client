from PyQt4 import QtCore, QtGui
from games.gameitem import GameItem, GameItemDelegate

from fa import maps
import util


RANKED_SEARCH_EXPANSION_TIME = 10000 #milliseconds before search radius expands

SEARCH_RADIUS_INCREMENT = 0.05
SEARCH_RADIUS_MAX = 0.25

FormClass, BaseClass = util.loadUiType("games/host.ui")


class HostgameWidget(FormClass, BaseClass):
    def __init__(self, parent, item, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)       

        self.setupUi(self)
        self.parent = parent
        
        self.parent.options = []

        if len(item.options) == 0 :   
            self.optionGroup.setVisible(False)
        else :
            group_layout = QtGui.QVBoxLayout()
            self.optionGroup.setLayout(group_layout)
            
            for option in item.options :
                checkBox = QtGui.QCheckBox(self)
                checkBox.setText(option)
                checkBox.setChecked(True)
                group_layout.addWidget(checkBox)
                self.parent.options.append(checkBox)
        
        
        self.setStyleSheet(self.parent.client.styleSheet())
        
        self.setWindowTitle ( "Hosting Game : " + item.name )
        self.titleEdit.setText ( self.parent.gamename )
        self.passEdit.setText ( self.parent.gamepassword )
        self.game = GameItem(0)
        self.gamePreview.setItemDelegate(GameItemDelegate(self));
        self.gamePreview.addItem(self.game)
        
        self.message = {}
        self.message['title'] = self.parent.gamename
        self.message['host'] = self.parent.client.login
        self.message['teams'] = {1:[self.parent.client.login]}
#        self.message.get('access', 'public')
        self.message['featured_mod'] = item.mod
        self.message['mapname'] = self.parent.gamemap
        self.message['state'] = "open"
        
        self.game.update(self.message, self.parent.client)
        
        i = 0
        index = 0
        
        for map in maps.maps :
            name = maps.getDisplayName(map)
            if map == self.parent.gamemap :
                index = i
            self.mapList.addItem(name, map)
            i = i + 1

        for map in maps.getUserMaps() :
            name = maps.getDisplayName(map)
            if map == self.parent.gamemap :
                index = i
            self.mapList.addItem(name, map)
            i = i + 1
        
        self.mapList.setCurrentIndex(index)
        
        icon = maps.preview(self.parent.gamemap, True)
        if not icon:
            icon = util.icon("games/unknown_map.png", False, True)

        #self.mapPreview.setPixmap(icon)
        
        self.mapList.currentIndexChanged.connect(self.mapChanged)
        self.hostButton.released.connect(self.hosting)
        self.titleEdit.textChanged.connect(self.updateText)
        
    def updateText(self, text):
        self.message['title'] = text
        self.game.update(self.message, self.parent.client)

    def hosting(self):
        self.parent.saveGameName(self.titleEdit.text().strip())
        self.parent.saveGameMap(self.parent.gamemap)
        if self.passCheck.isChecked() :
            self.parent.ispassworded = True
            self.parent.savePassword(self.passEdit.text())
        else :
            self.parent.ispassworded = False
        self.done(1)

    def mapChanged(self, index):
        self.parent.gamemap = self.mapList.itemData(index)
        icon = maps.preview(self.parent.gamemap, True)
        if not icon:
            icon = util.icon("games/unknown_map.png", False, True)
        #self.mapPreview.setPixmap(icon)        
        self.message['mapname'] = self.parent.gamemap
        self.game.update(self.message, self.parent.client)


