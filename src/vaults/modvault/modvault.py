from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from PyQt6 import QtCore
from PyQt6 import QtWidgets

from src.api.models.Map import Map
from src.api.models.Mod import Mod
from src.api.vaults_api import ModApiConnector
from src.vaults.modvault import utils
from src.vaults.modvault.moddetails import ModDetailsWidget
from src.vaults.modvault.modlistitem import ModDisplayType
from src.vaults.modvault.modlistitem import ModListItem
from src.vaults.modvault.modlistitem import ModSortType
from src.vaults.modvault.modlistwidget import ModListWidget
from src.vaults.vault import BrowseType
from src.vaults.vault import Vault

from .uimodwidget import UIModWidget
from .uploadwidget import UploadModWidget

if TYPE_CHECKING:
    from src.client._clientwindow import ClientWindow

logger = logging.getLogger(__name__)


class ModVault(Vault):
    def __init__(self, client: ClientWindow) -> None:
        Vault.__init__(self, client)
        logger.debug("Mod Vault tab instantiating")
        self.UIButton.clicked.connect(self.openUIModForm)
        self.uids = [mod.uid for mod in utils.getInstalledMods()]

        for sort_type in ModSortType:
            self.SortTypeList.addItem(sort_type.value)
        for display_type in ModDisplayType:
            self.ShowTypeList.addItem(display_type.value)

        self.apiConnector = ModApiConnector()
        self.apiConnector.data_ready.connect(self.items_info)

        most_played_row = self.browseComboBox.findText(BrowseType.MOST_PLAYED.value)
        self.browseComboBox.view().setRowHidden(most_played_row, True)
        item = self.browseComboBox.model().item(most_played_row)
        item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEnabled)

        self.UIButton.show()

    def create_item(self, data: Map | Mod) -> ModListWidget:
        assert isinstance(data, Mod)
        return ModListWidget(data)

    def create_list_item(self, data: Mod | Map) -> ModListItem:
        assert isinstance(data, Mod)
        return ModListItem(self.itemList, data)

    def create_details_widget(self, data: Map | Mod) -> ModDetailsWidget:
        assert self.client.me.player is not None
        return ModDetailsWidget(data, self.client.me.player)

    def on_item_availability_changed(self) -> None:
        current_item = self.itemList.currentItem()
        self.itemList.itemWidget(current_item).update_visibility()

    @QtCore.pyqtSlot()
    def openUIModForm(self):
        dialog = UIModWidget(self)
        dialog.exec()

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
                        "There were %s errors and %s warnings.",
                        modinfofile.error,
                        modinfofile.warnings,
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
                            QtWidgets.QMessageBox.StandardButton.Yes,
                            QtWidgets.QMessageBox.StandardButton.No,
                        )
                    else:
                        uploadmod = QtWidgets.QMessageBox.StandardButton.Yes
                    if uploadmod == QtWidgets.QMessageBox.StandardButton.Yes:
                        modinfo = utils.ModInfo(**modinfo)
                        modinfo.setFolder(os.path.split(modDir)[1])
                        modinfo.update()
                        dialog = UploadModWidget(self, modDir, modinfo)
                        dialog.exec()
            else:
                QtWidgets.QMessageBox.information(
                    self.client,
                    "Mod selection",
                    "This folder doesn't contain a mod_info.lua file",
                )
