"""
modInfo function is called when the client recieves a modvault_info command.
It should have a message dict with the following keys:
uid         - Unique identifier for a mod. Also needed ingame.
name        - Name of the mod. Also the name of the folder the mod will be
              located in.
description - A general description of the mod. As seen ingame
author      - The FAF username of the person that uploaded the mod.
downloads   - An integer containing the amount of downloads of this mod
likes       - An integer containing the amount of likes the mod has recieved.
              (TODO: Actually implement an inteface for this.)
comments    - A python list containing dictionaries containing the keys as
              described above.
bugreports  - A python list containing dictionaries containing the keys as
              described above.
date        - A string describing the date the mod was uploaded.
              Format: "%Y-%m-%d %H:%M:%S" eg: 2012-10-28 16:50:28
ui          - A boolean describing if it is a ui mod yay or nay.
link        - Direct link to the zip file containing the mod.
thumbnail   - A direct link to the thumbnail file. Should be something suitable
              for util.THEME.icon(). Not yet tested if this works correctly

Additional stuff:
fa.exe now has a CheckMods method, which is used in fa.exe.check
check has a new argument 'additional_mods' for this.
In client._clientwindow joinGameFromURL is changed. The url should have a
queryItemValue called 'mods' which with json can be translated in a list of
modnames so that it can be checked with checkMods.
handle_game_launch should have a new key in the form of mods, which is a list
of modnames to be checked with checkMods.

Stuff to be removed:
In _gameswidget.py in hostGameCLicked setActiveMods is called.
This should be done in the faf.exe.check function or in the lobby code.
It is here because the server doesn't yet send the mods info.

The tempAddMods function should be removed after the server can return mods in
the modvault.
"""

import logging
import os
import urllib.error
import urllib.parse
import urllib.request

from PyQt5 import QtCore, QtWidgets

import util
from api.vaults_api import ModApiConnector
from vaults.modvault import utils

from .modwidget import ModWidget
from .uimodwidget import UIModWidget
from .uploadwidget import UploadModWidget

from vaults.vault import Vault
from vaults.vault import VaultItem


logger = logging.getLogger(__name__)


class ModVault(Vault):
    def __init__(self, client, *args, **kwargs):
        QtCore.QObject.__init__(self, *args, **kwargs)
        Vault.__init__(self, client, *args, **kwargs)

        logger.debug("Mod Vault tab instantiating")

        self.itemList.itemDoubleClicked.connect(self.modClicked)
        self.UIButton.clicked.connect(self.openUIModForm)
        self.client.lobby_info.modVaultInfo.connect(self.modInfo)

        self.uids = [mod.uid for mod in utils.getInstalledMods()]

        for type_ in ["UI Only", "Sim Only", "Uploaded by You", "Installed"]:
            self.ShowTypeList.addItem(type_)

        self.apiConnector = ModApiConnector(self.client.lobby_dispatch)

        self.uploadButton.hide()

    @QtCore.pyqtSlot(dict)
    def modInfo(self, message):
        for value in message["values"]:
            uid = value["uid"]
            if uid not in self._items:
                mod = ModItem(self, uid)
                self._items[uid] = mod
                self.itemList.addItem(mod)
            else:
                mod = self._items[uid]
            mod.update(value)
        self.itemList.sortItems(1)

    @QtCore.pyqtSlot(int)
    def sortChanged(self, index):
        if index == -1 or index == 0:
            self.sortType = "alphabetical"
        elif index == 1:
            self.sortType = "date"
        elif index == 2:
            self.sortType = "rating"
        self.updateVisibilities()

    @QtCore.pyqtSlot(int)
    def showChanged(self, index):
        if index == -1 or index == 0:
            self.showType = "all"
        elif index == 1:
            self.showType = "ui"
        elif index == 2:
            self.showType = "sim"
        elif index == 3:
            self.showType = "yours"
        elif index == 4:
            self.showType = "installed"
        self.updateVisibilities()

    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem)
    def modClicked(self, item):
        widget = ModWidget(self, item)
        widget.exec_()

    @QtCore.pyqtSlot()
    def openUIModForm(self):
        dialog = UIModWidget(self)
        dialog.exec_()

    @QtCore.pyqtSlot()
    def openUploadForm(self):
        modDir = QtWidgets.QFileDialog.getExistingDirectory(
            self.client,
            "Select the mod directory to upload",
            utils.MODFOLDER,
            QtWidgets.QFileDialog.ShowDirsOnly,
        )
        logger.debug("Uploading mod from: " + modDir)
        if modDir != "":
            if utils.isModFolderValid(modDir):
                # os.chmod(modDir, S_IWRITE) Don't need this at the moment
                modinfofile, modinfo = utils.parseModInfo(modDir)
                if modinfofile.error:
                    logger.debug(
                        "There were {} errors and {} warnings.".format(
                            modinfofile.error,
                            modinfofile.warnings,
                        ),
                    )
                    logger.debug(modinfofile.errorMsg)
                    QtWidgets.QMessageBox.critical(
                        self.client,
                        "Lua parsing error",
                        modinfofile.errorMsg + "\nMod uploading cancelled.",
                    )
                else:
                    if modinfofile.warning:
                        uploadmod = QtWidgets.QMessageBox.question(
                            self.client,
                            "Lua parsing warning",
                            (
                                modinfofile.errorMsg
                                + "\nDo you want to upload the mod?"
                            ),
                            QtWidgets.QMessageBox.Yes,
                            QtWidgets.QMessageBox.No,
                        )
                    else:
                        uploadmod = QtWidgets.QMessageBox.Yes
                    if uploadmod == QtWidgets.QMessageBox.Yes:
                        modinfo = utils.ModInfo(**modinfo)
                        modinfo.setFolder(os.path.split(modDir)[1])
                        modinfo.update()
                        dialog = UploadModWidget(self, modDir, modinfo)
                        dialog.exec_()
            else:
                QtWidgets.QMessageBox.information(
                    self.client,
                    "Mod selection",
                    "This folder doesn't contain a mod_info.lua file",
                )

    def downloadMod(self, mod):
        if utils.downloadMod(mod):
            self.uids = [mod.uid for mod in utils.getInstalledMods()]
            self.updateVisibilities()
            return True
        else:
            return False

    def removeMod(self, mod):
        if utils.removeMod(mod):
            self.uids = [m.uid for m in utils.installedMods]
            mod.updateVisibility()


class ModItem(VaultItem):
    def __init__(self, parent, uid, *args, **kwargs):
        VaultItem.__init__(self, parent, *args, **kwargs)

        self.formatterItem = str(
            util.THEME.readfile("vaults/modvault/modinfo.qthtml"),
        )

        self.uid = uid
        self.author = ""
        self.thumbstr = ""
        self.isuidmod = False
        self.uploadedbyuser = False

    def shouldBeVisible(self):
        p = self.parent
        if p.showType == "all":
            return True
        elif p.showType == "ui":
            return self.isuimod
        elif p.showType == "sim":
            return not self.isuimod
        elif p.showType == "yours":
            return self.uploadedbyuser
        elif p.showType == "installed":
            return self.uid in self.parent.uids
        else:
            return True

    def update(self, item_dict):
        self.name = item_dict["name"]
        self.description = item_dict["description"]
        self.version = item_dict["version"]
        self.author = item_dict["author"]
        self.rating = item_dict["rating"]
        self.reviews = item_dict["reviews"]
        self.date = item_dict['date'][:10]
        self.isuimod = item_dict["ui"]
        self.link = item_dict["link"]
        self.thumbstr = item_dict["thumbnail"]
        self.uploadedbyuser = (self.author == self.parent.client.login)

        if self.thumbstr == "":
            self.setItemIcon("games/unknown_map.png")
        else:
            name = os.path.basename(urllib.parse.unquote(self.thumbstr))
            img = utils.getIcon(name)
            if img:
                self.setItemIcon(img, False)
            else:
                self.parent.client.mod_downloader.download_preview(
                    name[:-4], self._item_dl_request, self.thumbstr,
                )

        VaultItem.update(self)

    def updateVisibility(self):
        if self.isuimod:
            self.itemType_ = "UI mod"
        if self.uid in self.parent.uids:
            self.color = "green"
        else:
            self.color = "white"

        self.setText(
            self.formatterItem.format(
                color=self.color,
                version=self.version,
                title=self.name,
                description=self.trimmedDescription,
                rating=self.rating,
                reviews=self.reviews,
                date=self.date,
                modtype=self.itemType_,
                author=self.author,
            ),
        )

        VaultItem.updateVisibility(self)
