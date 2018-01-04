"""
Modvault database documentation:
command = "modvault"
possible commands (value for the 'type' key):
    start: <no args> - given when the tab is opened. Signals that the server should send the possible mods.
    addcomment: moduid=<uid of the mod the comment belongs to>, comment={"or","uid","date","text"} 
    addbugreport: moduid=<uid of the mod the comment belongs to>, comment={"author","uid","date","text"}
    like: uid-<the uid of the mod that was liked>

Can also send a UPLOAD_MOD command directly using writeToServer
"UPLOAD_MOD","modname.zip",{mod info}, qfile

modInfo function is called when the client receives a modvault_info command.
It should have a message dict with the following keys:
uid         - Unique identifier for a mod. Also needed ingame.
name        - Name of the mod. Also the name of the folder the mod will be located in.
description - A general description of the mod. As seen ingame
author      - The FAF username of the person that uploaded the mod.
downloads   - An integer containing the amount of downloads of this mod
likes       - An integer containing the amount of likes the mod has received. #TODO: Actually implement an inteface for this.
comments    - A python list containing dictionaries containing the keys as described above.
bugreports  - A python list containing dictionaries containing the keys as described above.
date        - A string describing the date the mod was uploaded. Format: "%Y-%m-%d %H:%M:%S" eg: 2012-10-28 16:50:28
ui          - A boolean describing if it is a ui mod yay or nay.
link        - Direct link to the zip file containing the mod.
thumbnail   - A direct link to the thumbnail file. Should be something suitable for util.THEME.icon().

Additional stuff:
fa.exe now has a CheckMods method, which is used in fa.exe.check
check has a new argument 'additional_mods' for this.
In client._clientwindow joinGameFromURL is changed. The url should have a
queryItemValue called 'mods' which with json can be translated in a list of modnames
so that it can be checked with checkMods.
handle_game_launch should have a new key in the form of mods, which is a list of modnames
to be checked with checkMods.

Stuff to be removed:
In hostgamewidget.py in hosting and _launch_game setActiveMods is called.
This should be done in the faf.exe.check function or in the lobby code.
It is here because the server doesn't yet send the mods info.
"""

import os
from PyQt5 import QtCore, QtWidgets
from . import utils
from .modmodel import ModFilterModel
from .modwidget import ModWidget
from .uploadwidget import UploadModWidget
from .uimodwidget import UIModWidget
from ui.busy_widget import BusyWidget

import util
import logging
logger = logging.getLogger(__name__)

FormClass, BaseClass = util.THEME.loadUiType("modvault/modvault.ui")


class ModVault(FormClass, BaseClass, BusyWidget):

    def __init__(self, client, mod_model, modview_builder):
        BaseClass.__init__(self)
        self.setupUi(self)

        self.client = client

        logger.debug("Mod Vault tab instantiating")
        self._mod_model = ModFilterModel(mod_model)
        self.modview = modview_builder(self._mod_model, self.modList)
        self.modview.mod_double_clicked.connect(self.mod_double_clicked)
        self.modview._delegate.painting.connect(self.info_update)

        self.searchButton.clicked.connect(self.server_search)
        self.searchInput.returnPressed.connect(self.filter_search)
        self.uploadButton.clicked.connect(self.openUploadForm)
        self.UIButton.clicked.connect(self.openUIModForm)

        self.SortType.setCurrentIndex(2)
        self.SortType.currentIndexChanged.connect(self.sort_changed)
        self.ShowType.currentIndexChanged.connect(self.show_changed)

        self.showType = "all"

        self.uids = [mod.uid for mod in utils.getInstalledMods()]

    @QtCore.pyqtSlot(int)
    def sort_changed(self, index):
        self._mod_model.sort_type = ModFilterModel.SortType(index)

    @QtCore.pyqtSlot(int)
    def show_changed(self, index):
        self._mod_model.filter_type = ModFilterModel.FilterType(index)
        self.info_update()  # in case search returns nothing

    def mod_double_clicked(self, mod):
        widget = ModWidget(self, mod)
        widget.exec_()

    def info_update(self):
        self.labelInfo.setText("showing {} of {} mods / {} installed mods".
                               format(self._mod_model.rowCount(), len(self.client.modset.mods), len(self.uids)))

    def server_search(self):
        """ Sending search to mod server"""
        search_str = self.searchInput.text().lower()
        self._mod_model.search_str = search_str
        index = self.ShowType.currentIndex()
        if index == 1:  # UI Only
            typemod = 1
        elif index == 2:  # Sim Only
            typemod = 0
        else:  # All, yours, installed
            typemod = 2

        self.client.statsServer.send(dict(command="modvault_search", typemod=typemod, search=search_str))

    def filter_search(self):
        """ filter mods with search string"""
        search_str = self.searchInput.text().lower()
        self._mod_model.search_str = search_str
        self.info_update()  # in case search returns nothing

    @QtCore.pyqtSlot()
    def openUIModForm(self):
        dialog = UIModWidget(self)
        dialog.exec_()

    @QtCore.pyqtSlot()
    def openUploadForm(self):
        modDir = QtWidgets.QFileDialog.getExistingDirectory(self.client, "Select the mod directory to upload",
                                                            utils.MODFOLDER,  QtWidgets.QFileDialog.ShowDirsOnly)
        logger.debug("Uploading mod from: " + modDir)
        if modDir != "":
            if utils.isModFolderValid(modDir):
                # os.chmod(modDir, S_IWRITE) Don't need this at the moment
                modinfofile, modinfo = utils.parseModInfo(modDir)
                if modinfofile.error:
                    logger.debug("There were " + str(modinfofile.errors) + " errors and " +
                                 str(modinfofile.warnings) + " warnings.")
                    logger.debug(modinfofile.errorMsg)
                    QtWidgets.QMessageBox.critical(self.client, "Lua parsing error", modinfofile.errorMsg +
                                                   "\nMod uploading cancelled.")
                else:
                    if modinfofile.warning:
                        uploadmod = QtWidgets.QMessageBox.question(self.client, "Lua parsing warning",
                                                                   modinfofile.errorMsg +
                                                                   "\nDo you want to upload the mod?",
                                                                   QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
                    else:
                        uploadmod = QtWidgets.QMessageBox.Yes
                    if uploadmod == QtWidgets.QMessageBox.Yes:
                        modinfo = utils.ModInfo(**modinfo)
                        modinfo.setFolder(os.path.split(modDir)[1])
                        modinfo.update()
                        dialog = UploadModWidget(self, modDir, modinfo)
                        dialog.exec_()
            else:
                QtWidgets.QMessageBox.information(self.client, "Mod selection",
                                                  "This folder doesn't contain a mod_info.lua file")

    @QtCore.pyqtSlot()
    def busy_entered(self):
        self.client.lobby_connection.send(dict(command="modvault", type="start"))

    def download_mod(self, mod):
        if utils.downloadMod(mod):
            self.client.lobby_connection.send(dict(command="modvault", type="download", uid=mod.uid))
            self.uids = [mod.uid for mod in utils.getInstalledMods()]
            mod.installed = mod.uid in self.uids
            return True
        else:
            return False

    def remove_mod(self, mod):
        if utils.removeMod(mod):
            self.uids = [m.uid for m in utils.installedMods]
            mod.installed = mod.uid in self.uids
