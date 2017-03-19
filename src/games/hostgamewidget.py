import os

from PyQt5 import QtCore, QtWidgets
from games.gameitem import GameItem, GameItemDelegate
import modvault

from fa import maps
import util
import fa.check

import logging
logger = logging.getLogger(__name__)

FormClass, BaseClass = util.loadUiType("games/host.ui")

class HostgameWidget(FormClass, BaseClass):
    def __init__(self, parent, item, iscoop=False, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)

        self.setupUi(self)
        self.parent = parent
        self.iscoop = iscoop
        self.featured_mod = item.mod

        self.setStyleSheet(self.parent.client.styleSheet())
        # load settings
        util.settings.beginGroup("fa.games")
        # Default of "password"
        self.password = util.settings.value("password", "password")
        self.title = util.settings.value("gamename", (self.parent.client.login or "") + "'s game")
        self.friends_only = util.settings.value("friends_only", False, type=bool)
        if self.iscoop:
            self.mapname = fa.maps.link2name(item.mapUrl)
        else:
            self.mapname = util.settings.value("gamemap", "scmp_007")
        util.settings.endGroup()

        self.setWindowTitle ( "Hosting Game : " + item.name )
        self.titleEdit.setText(self.title)
        self.passEdit.setText(self.password)
        self.game = GameItem(0)
        self.gamePreview.setItemDelegate(GameItemDelegate(self))
        self.gamePreview.addItem(self.game)
        
        self.message = {
            "title": self.title,
            "host": self.parent.client.login, # We will want to send our ID here at some point
            "teams": {1:[self.parent.client.id]},
            "featured_mod": self.featured_mod,
            "mapname": self.mapname,
            "state": "open",
        }

        self.game.update(self.message)
        self.game.setHidden(False)
        
        i = 0
        index = 0
        if not self.iscoop:
            allmaps = dict()
            for map in list(maps.maps.keys()) + maps.getUserMaps():
                allmaps[map] = maps.getDisplayName(map)
            for (map, name) in sorted(iter(allmaps.items()), key=lambda x: x[1]):
                if map == self.mapname :
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

        names = [mod.totalname for mod in modvault.getActiveMods(uimods=False, temporary=False)]
        logger.debug("Active Mods detected: %s" % str(names))
        for name in names:
            l = self.modList.findItems(name, QtCore.Qt.MatchExactly)
            logger.debug("found item: %s" % l[0].text())
            if l: l[0].setSelected(True)

        self.radioFriends.setChecked(self.friends_only)

        self.mapList.currentIndexChanged.connect(self.mapChanged)
        self.hostButton.released.connect(self.hosting)
        self.titleEdit.textChanged.connect(self.updateText)
        #self.modList.itemClicked.connect(self.modclicked)
        
    def updateText(self, text):
        self.message['title'] = text
        self.game.update(self.message)
        self.game.setHidden(False)

    def hosting(self):
        name = self.titleEdit.text().strip()
        if len(name) == 0:
            # TODO: Feedback to the UI that the name must not be blank.
            return
        self.title = name

        self.friends_only = self.radioFriends.isChecked()
        if self.passCheck.isChecked():
            self.password = self.passEdit.text()
        else:
            self.password = None
        self.save_last_hosted_settings()

        # Make sure the binaries are all up to date, and abort if the update fails or is cancelled.
        if not fa.check.game(self.parent.client):
            return

        # Ensure all mods are up-to-date, and abort if the update process fails.
        if not fa.check.check(self.featured_mod):
            return
        if self.iscoop and not fa.check.map_(self.mapname, force=True):
            return

        modnames = [str(moditem.text()) for moditem in self.modList.selectedItems()]
        mods = [self.mods[modstr] for modstr in modnames]
        modvault.setActiveMods(mods, True, False)

        self.parent.client.host_game(title=self.title,
                                 mod=self.featured_mod,
                                 visibility="friends" if self.friends_only else "public",
                                 mapname=self.mapname,
                                 password=self.password)


        self.done(1)
        return


    def mapChanged(self, index):
        self.mapname = self.mapList.itemData(index)

        self.message['mapname'] = self.mapname
        self.game.update(self.message)

    def save_last_hosted_settings(self):
        util.settings.beginGroup("fa.games")
        if not self.iscoop:
            util.settings.setValue("gamemap", self.mapname)
        if self.title != "Nobody's game":
            util.settings.setValue("gamename", self.title)
        util.settings.setValue("friends_only", self.radioFriends.isChecked())

        if self.password is not None:
            util.settings.setValue("password", self.password)
        util.settings.endGroup()
