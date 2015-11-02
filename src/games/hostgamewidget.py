import os

from PyQt4 import QtCore, QtGui
from games.gameitem import GameItem, GameItemDelegate
import modvault

from fa import maps
import util

import logging
logger = logging.getLogger(__name__)

FormClass, BaseClass = util.loadUiType("games/host.ui")

class HostgameWidget(FormClass, BaseClass):
    def __init__(self, parent, item, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)

        self.setupUi(self)
        self.parent = parent

        self.setStyleSheet(self.parent.client.styleSheet())

        self.setWindowTitle ( "Hosting Game : " + item.name )
        self.titleEdit.setText ( self.parent.gamename )
        self.passEdit.setText ( self.parent.gamepassword )
        self.game = GameItem(0)
        self.gamePreview.setItemDelegate(GameItemDelegate(self))
        self.gamePreview.addItem(self.game)
        
        self.message = {
            "title": self.parent.gamename,
            "host": self.parent.client.id,
            "teams": {1:[self.parent.client.id]},
            "featured_mod": "faf",
            "mapname": self.parent.gamemap,
            "state": "open",
        }

        self.game.update(self.message, self.parent.client)
        
        i = 0
        index = 0
        if self.parent.canChooseMap == True:
            allmaps = dict()
            for map in maps.maps.keys() + maps.getUserMaps():
                allmaps[map] = maps.getDisplayName(map)
            for (map, name) in sorted(allmaps.iteritems(), key=lambda x: x[1]):
                if map == self.parent.gamemap :
                    index = i
                self.mapList.addItem(name, map)
                i = i + 1
            self.mapList.setCurrentIndex(index)
        else:
            self.mapList.hide()

        self.mods = {}
        #this makes it so you can select every non-ui_only mod
        for mod in modvault.getInstalledMods():
            if mod.ui_only:
                continue
            self.mods[mod.totalname] = mod
            self.modList.addItem(mod.totalname)

        names = [mod.totalname for mod in modvault.getActiveMods(uimods=False)]
        logger.debug("Active Mods detected: %s" % str(names))
        for name in names:
            l = self.modList.findItems(name, QtCore.Qt.MatchExactly)
            logger.debug("found item: %s" % l[0].text())
            if l: l[0].setSelected(True)

        self.radioFriends.setChecked(self.parent.friends_only)

        self.mapList.currentIndexChanged.connect(self.mapChanged)
        self.hostButton.released.connect(self.hosting)
        self.titleEdit.textChanged.connect(self.updateText)
        #self.modList.itemClicked.connect(self.modclicked)
        
    def updateText(self, text):
        self.message['title'] = text
        self.game.update(self.message, self.parent.client)

    def hosting(self):
        name = self.titleEdit.text().strip()
        if len(name) == 0:
            # TODO: Feedback to the UI that the name must not be blank.
            return

        if self.passCheck.isChecked():
            password = self.passEdit.text()
        else:
            password = None

        # TODO: Remove this ridiculous use of a parent pointer.
        map = self.parent.gamemap

        self.parent.save_last_hosted_settings(name, map, password, self.radioFriends.isChecked())
        self.done(1)

    def mapChanged(self, index):
        self.parent.gamemap = self.mapList.itemData(index)

        self.message['mapname'] = self.parent.gamemap
        self.game.update(self.message, self.parent.client)
