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

modInfo function is called when the client recieves a modvault_info command.
It should have a message dict with the following keys:
uid         - Unique identifier for a mod. Also needed ingame.
name        - Name of the mod. Also the name of the folder the mod will be located in.
description - A general description of the mod. As seen ingame
author      - The FAF username of the person that uploaded the mod.
downloads   - An integer containing the amount of downloads of this mod
likes       - An integer containing the amount of likes the mod has recieved. #TODO: Actually implement an inteface for this.
comments    - A python list containing dictionaries containing the keys as described above.
bugreports  - A python list containing dictionaries containing the keys as described above.
date        - A string describing the date the mod was uploaded. Format: "%Y-%m-%d %H:%M:%S" eg: 2012-10-28 16:50:28
ui          - A boolean describing if it is a ui mod yay or nay.
link        - Direct link to the zip file containing the mod.
thumbnail   - A direct link to the thumbnail file. Should be something suitable for util.THEME.icon(). Not yet tested if this works correctly

Additional stuff:
fa.exe now has a CheckMods method, which is used in fa.exe.check
check has a new argument 'additional_mods' for this.
In client._clientwindow joinGameFromURL is changed. The url should have a
queryItemValue called 'mods' which with json can be translated in a list of modnames
so that it can be checked with checkMods.
handle_game_launch should have a new key in the form of mods, which is a list of modnames
to be checked with checkMods.

Stuff to be removed:
In _gameswidget.py in hostGameCLicked setActiveMods is called.
This should be done in the faf.exe.check function or in the lobby code.
It is here because the server doesn't yet send the mods info.

The tempAddMods function should be removed after the server can return mods in the modvault.
"""

import logging
import os
import time
import zipfile
from datetime import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

import util
from api.vaults_api import ModApiConnector
from modvault.utils import *
from ui.busy_widget import BusyWidget

from .modwidget import ModWidget
from .uimodwidget import UIModWidget
from .uploadwidget import UploadModWidget

logger = logging.getLogger(__name__)
import urllib.error
import urllib.parse
import urllib.request

from downloadManager import DownloadRequest

FormClass, BaseClass = util.THEME.loadUiType("modvault/modvault.ui")


class ModVault(FormClass, BaseClass, BusyWidget):
    def __init__(self, client, *args, **kwargs):
        QtCore.QObject.__init__(self, *args, **kwargs)

        self.setupUi(self)

        self.client = client  # type: ClientWindow

        logger.debug("Mod Vault tab instantiating")
        self.loaded = False

        self.modList.setItemDelegate(ModItemDelegate(self))
        self.modList.itemDoubleClicked.connect(self.modClicked)
        self.searchButton.clicked.connect(self.search)
        self.searchInput.returnPressed.connect(self.search)
        self.uploadButton.clicked.connect(self.openUploadForm)
        self.UIButton.clicked.connect(self.openUIModForm)

        self.SortType.setCurrentIndex(0)
        self.SortType.currentIndexChanged.connect(self.sortChanged)
        self.ShowType.currentIndexChanged.connect(self.showChanged)

        self.client.lobby_info.modVaultInfo.connect(self.modInfo)
        self.client.lobby_info.vaultMeta.connect(self.metaInfo)

        self.sortType = "alphabetical"
        self.showType = "all"
        self.searchString = ""
        self.searchQuery = dict(include = 'latestVersion,reviewsSummary')

        self.pageSize = self.quantityBox.value()
        self.pageNumber = 1

        self.goToPageButton.clicked.connect(lambda: self.goToPage(self.pageBox.value()))
        self.pageBox.setValue(self.pageNumber)
        self.pageBox.valueChanged.connect(self.checkTotalPages)
        self.totalPages = 1
        self.totalRecords = None
        self.quantityBox.valueChanged.connect(self.checkPageSize)
        self.nextButton.clicked.connect(lambda: self.goToPage(self.pageBox.value() + 1))
        self.previousButton.clicked.connect(lambda: self.goToPage(self.pageBox.value() - 1))
        self.firstButton.clicked.connect(lambda: self.goToPage(1))
        self.lastButton.clicked.connect(lambda: self.goToPage(self.totalPages))
        self.resetButton.clicked.connect(self.resetSearch)

        self.mods = {}
        self.uids = [mod.uid for mod in getInstalledMods()]

        self.apiConnector = ModApiConnector(self.client.lobby_dispatch)

    @QtCore.pyqtSlot(int)
    def checkPageSize(self):
        self.pageSize = self.quantityBox.value()

    @QtCore.pyqtSlot(int)
    def checkTotalPages(self):
        if self.pageBox.value() > self.totalPages:
            self.pageBox.setValue(self.totalPages)

    def updateQuery(self, pageNumber):
        self.searchQuery['page[size]'] = self.pageSize
        self.searchQuery['page[number]'] = pageNumber
        self.searchQuery['page[totals]'] = None

    @QtCore.pyqtSlot(bool)
    def goToPage(self, page):
        self.mods.clear()
        self.modList.clear()
        self.pageBox.setValue(page)
        self.pageNumber = self.pageBox.value()
        self.pageBox.setValue(self.pageNumber)
        self.updateQuery(self.pageNumber)
        self.apiConnector.requestMod(self.searchQuery)
        self.updateVisibilities()

    @QtCore.pyqtSlot(dict)
    def metaInfo(self, message):
        self.totalPages = message['page']['totalPages']
        self.totalRecords = message['page']['totalRecords']
        if self.totalPages < 1:
            self.totalPages = 1
        self.labelTotalPages.setText(str(self.totalPages))

    @QtCore.pyqtSlot(bool)
    def resetSearch(self):
        self.searchString = ''
        self.searchInput.clear()
        self.searchQuery = dict(include = 'latestVersion,reviewsSummary')
        self.goToPage(1)

    @QtCore.pyqtSlot(dict)
    def modInfo(self, message):
        for value in message["values"]:
            uid = value["uid"]
            if not uid in self.mods:
                mod = ModItem(self, uid)
                self.mods[uid] = mod
                self.modList.addItem(mod)
            else:
                mod = self.mods[uid]
            mod.update(value)
        self.modList.sortItems(1)

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

    def search(self):
        """ Sending search to mod server"""
        self.searchString = self.searchInput.text().lower()
        if self.searchString == '' or self.searchString.replace(' ', '') == '':
            self.resetSearch()
        else:
            self.searchString = self.searchString.strip()
            self.searchQuery = dict(include = 'latestVersion,reviewsSummary', filter = 'displayName==' + '"*' + self.searchString + '*"')
            self.goToPage(1)

    @QtCore.pyqtSlot()
    def openUIModForm(self):
        dialog = UIModWidget(self)
        dialog.exec_()

    @QtCore.pyqtSlot()
    def openUploadForm(self):
        modDir = QtWidgets.QFileDialog.getExistingDirectory(self.client, "Select the mod directory to upload",
                                                            MODFOLDER,  QtWidgets.QFileDialog.ShowDirsOnly)
        logger.debug("Uploading mod from: " + modDir)
        if modDir != "":
            if isModFolderValid(modDir):
                # os.chmod(modDir, S_IWRITE) Don't need this at the moment
                modinfofile, modinfo = parseModInfo(modDir)
                if modinfofile.error:
                    logger.debug("There were " + str(modinfofile.errors) + " errors and " + str(modinfofile.warnings) +
                                 " warnings.")
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
                        modinfo = ModInfo(**modinfo)
                        modinfo.setFolder(os.path.split(modDir)[1])
                        modinfo.update()
                        dialog = UploadModWidget(self, modDir, modinfo)
                        dialog.exec_()
            else:
                QtWidgets.QMessageBox.information(self.client, "Mod selection",
                                                  "This folder doesn't contain a mod_info.lua file")

    @QtCore.pyqtSlot()
    def busy_entered(self):
        if not self.mods:
            self.goToPage(self.pageNumber)

    def updateVisibilities(self):
        logger.debug("Updating visibilities with sort '%s' and visibility '%s'" % (self.sortType, self.showType))
        for mod in self.mods:
            self.mods[mod].updateVisibility()
        self.modList.sortItems(1)

    def downloadMod(self, mod):
        if downloadMod(mod):
            self.client.lobby_connection.send(dict(command="modvault", type="download", uid=mod.uid))
            self.uids = [mod.uid for mod in getInstalledMods()]
            self.updateVisibilities()
            return True
        else:
            return False

    def removeMod(self, mod):
        if removeMod(mod):
            self.uids = [m.uid for m in installedMods]
            mod.updateVisibility()


# the drawing helper function for the modlist
class ModItemDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, *args, **kwargs):
        QtWidgets.QStyledItemDelegate.__init__(self, *args, **kwargs)

    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)

        painter.save()

        html = QtGui.QTextDocument()
        html.setHtml(option.text)

        icon = QtGui.QIcon(option.icon)
        iconsize = QtCore.QSize(ModItem.ICONSIZE, ModItem.ICONSIZE)
        # clear icon and text before letting the control draw itself because we're rendering these parts ourselves
        option.icon = QtGui.QIcon()
        option.text = ""  
        option.widget.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, painter, option.widget)

        # Shadow
        painter.fillRect(option.rect.left()+8-1, option.rect.top()+8-1, iconsize.width(), iconsize.height(), QtGui.QColor("#202020"))

        iconrect = option.rect.adjusted(3,3,0,0)
        iconrect.setSize(iconsize)
        # Icon
        icon.paint(painter, iconrect, QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)

        # Frame around the icon
        pen = QtGui.QPen()
        pen.setWidth(1)
        pen.setBrush(QtGui.QColor("#303030"))  # FIXME: This needs to come from theme.
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawRect(iconrect)

        # Description
        painter.translate(option.rect.left() + iconsize.width() + 10, option.rect.top()+4)
        clip = QtCore.QRectF(0, 0, option.rect.width()-iconsize.width() - 10 - 5, option.rect.height())
        html.drawContents(painter, clip)

        painter.restore()

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)

        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        html.setTextWidth(ModItem.TEXTWIDTH)
        return QtCore.QSize(ModItem.ICONSIZE + ModItem.TEXTWIDTH + ModItem.PADDING, ModItem.ICONSIZE + ModItem.PADDING)   


class ModItem(QtWidgets.QListWidgetItem):
    TEXTWIDTH = 230
    ICONSIZE = 100
    PADDING = 10
    
    WIDTH = ICONSIZE + TEXTWIDTH
    #DATA_PLAYERS = 32

    FORMATTER_MOD = str(util.THEME.readfile("modvault/modinfo.qthtml"))
    FORMATTER_MOD_UI = str(util.THEME.readfile("modvault/modinfoui.qthtml"))

    def __init__(self, parent, uid, *args, **kwargs):
        QtWidgets.QListWidgetItem.__init__(self, *args, **kwargs)

        self.parent = parent
        self.uid = uid
        self.name = ""
        self.description = ""
        self.author = ""
        self.version = 0
        self.rating = 0
        self.reviews = 0
        self.comments = []  # every element is a dictionary with a
        self.bugreports = []  # text, author and date key
        self.date = None
        self.isuidmod = False
        self.uploadedbyuser = False

        self.link = ""
        self.loadThread = None
        self.setHidden(True)

        self._map_dl_request = DownloadRequest()
        self._map_dl_request.done.connect(self._on_mod_downloaded)

    def update(self, dic):
        self.name = dic["name"]
        self.description = dic["description"]
        self.version = dic["version"]
        self.author = dic["author"]
        self.rating = dic["rating"]
        self.reviews = dic["reviews"]
        #self.comments = dic["comments"]
        #self.bugreports = dic["bugreports"]
        self.date = dic['date'][:10]
        self.isuimod = dic["ui"]
        self.link = dic["link"]  # Direct link to the zip file.
        self.thumbstr = dic["thumbnail"]  # direct url to the thumbnail file.
        self.uploadedbyuser = (self.author == self.parent.client.login)

        if self.thumbstr == "":
            self.setItemIcon("games/unknown_map.png")
        else:
            name = os.path.basename(urllib.parse.unquote(self.thumbstr))
            img = getIcon(name)
            if img:
                self.setItemIcon(img, False)
            else:
                self.parent.client.mod_downloader.download_preview(name[:-4], self._map_dl_request, self.thumbstr)
                
        #ensure that the icon is set
        self.ensureIcon()

        self.updateVisibility()

    def setItemIcon(self, filename, themed=True):
        icon = util.THEME.icon(filename, themed)
        if not themed:
            pixmap = QtGui.QPixmap(filename)
            if not pixmap.isNull():
                icon.addPixmap(pixmap.scaled(QtCore.QSize(self.ICONSIZE, self.ICONSIZE)))
        self.setIcon(icon)

    def ensureIcon(self):
        if self.icon() is None or self.icon().isNull():
            self.setItemIcon("games/unknown_map.png")

    def _on_mod_downloaded(self, modname, result):
        path, is_local = result
        self.setItemIcon(path, is_local)
        self.ensureIcon()

    def shouldBeVisible(self):
        p = self.parent
        if p.searchString != "":
            if not (self.author.lower().find(p.searchString) != -1 or self.name.lower().find(p.searchString) != -1 or
                            self.description.lower().find(" " + p.searchString + " ") != -1):
                return False
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
        else:  # shouldn't happen
            return True

    def updateVisibility(self):
        self.setHidden(not self.shouldBeVisible())
        if len(self.description) < 200:
            descr = self.description
        else:
            descr = self.description[:197] + "..."

        modtype = ""
        if self.isuimod:
            modtype = "UI mod"
        if self.uid in self.parent.uids:
            color = "green"
        else:
            color = "white"

        self.setText(self.FORMATTER_MOD.format(color=color, version=str(self.version), title=self.name,
                                               description=descr, author=self.author, rating=str(self.rating),
                                               reviews=str(self.reviews), date=str(self.date), modtype=modtype))

        self.setToolTip('<p width="230">%s</p>' % self.description)

    def __ge__(self, other):
        return not self.__lt__(self, other)

    def __lt__(self, other):
        if self.parent.sortType == "alphabetical":
            if self.name.lower() == other.name.lower():
                return self.uid < other.uid
            return self.name.lower() > other.name.lower()
        elif self.parent.sortType == "rating":
            if self.rating == other.rating:
                return self.reviews < other.reviews
            return self.rating < other.rating
        elif self.parent.sortType == "date":
            # guard
            if self.date is None:
                return other.date is not None
            if self.date == other.date:
                return self.name.lower() > other.name.lower()
            return self.date < other.date
