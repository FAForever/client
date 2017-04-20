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
thumbnail   - A direct link to the thumbnail file. Should be something suitable for util.icon(). Not yet tested if this works correctly

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

import os

import zipfile

from PyQt4 import QtCore, QtGui

from modvault.utils import *
from .modwidget import ModWidget
from .uploadwidget import UploadModWidget
from .uimodwidget import UIModWidget

import util
import logging
import time
logger = logging.getLogger(__name__)
import urllib.request, urllib.error, urllib.parse

from util import datetostr, now
d = datetostr(now())
'''
tempmod1 = dict(uid=1,name='Mod1', comments=[],bugreports=[], date = d,
                ui=True, downloads=0, likes=0,
                thumbnail="",author='johnie102',
                description="""Lorem ipsum dolor sit amet, consectetur adipiscing elit. """,)
'''

FormClass, BaseClass = util.loadUiType("modvault/modvault.ui")

class ModVault(FormClass, BaseClass):
    def __init__(self, client, *args, **kwargs):
        QtCore.QObject.__init__(self, *args, **kwargs)

        self.setupUi(self)
        
        self.client = client
        self.client.modsTab.layout().addWidget(self)

        logger.debug("Mod Vault tab instantiating")
        self.loaded = False

        self.modList.setItemDelegate(ModItemDelegate(self))
        self.modList.itemDoubleClicked.connect(self.modClicked)
        self.searchButton.clicked.connect(self.search)
        self.searchInput.returnPressed.connect(self.search)
        self.uploadButton.clicked.connect(self.openUploadForm)
        self.UIButton.clicked.connect(self.openUIModForm)

        self.SortType.setCurrentIndex(2)
        self.SortType.currentIndexChanged.connect(self.sortChanged)
        self.ShowType.currentIndexChanged.connect(self.showChanged)
        
        
        self.client.showMods.connect(self.tabOpened)
        self.client.lobby_info.modVaultInfo.connect(self.modInfo)

        self.sortType = "rating"
        self.showType = "all"
        self.searchString = ""

        self.mods = {}
        self.uids = [mod.uid for mod in getInstalledMods()]

    @QtCore.pyqtSlot(dict)
    def modInfo(self, message): #this is called when the database has send a mod to us
        """
        See above for the keys neccessary in message.
        """
        uid = message["uid"]
        if not uid in self.mods:
            mod = ModItem(self, uid)
            self.mods[uid] = mod
            self.modList.addItem(mod)
        else : 
            mod = self.mods[uid]
        mod.update(message)
        self.modList.sortItems(1)
        
        

    @QtCore.pyqtSlot(int)
    def sortChanged(self, index):
        if index == -1 or index == 0:
            self.sortType = "alphabetical"
        elif index == 1:
            self.sortType = "date"
        elif index == 2:
            self.sortType = "rating"
        elif index == 3:
            self.sortType = "downloads"
        self.updateVisibilities()

    @QtCore.pyqtSlot(int)
    def showChanged(self, index):
        if index == -1 or index == 0:
            self.showType = "all"
        elif index == 1:
            self.showType = "ui"
        elif index == 2:
            self.showType = "sim"
        elif index == 5:
            self.showType = "yours"
        elif index == 6:
            self.showType = "installed"
        self.updateVisibilities()
    

    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def modClicked(self, item):
        widget = ModWidget(self, item)
        widget.exec_()

    def search(self):
        ''' Sending search to mod server'''
        
        self.searchString = self.searchInput.text().lower()
        index = self.ShowType.currentIndex()
        typemod = 2

        if index == 1:
            typemod = 1
        elif index == 2:
            typemod = 0

        self.client.statsServer.send(dict(command="modvault_search", typemod=typemod, search=self.searchString))
        
        self.updateVisibilities()

    @QtCore.pyqtSlot()
    def openUIModForm(self):
        dialog = UIModWidget(self)
        dialog.exec_()
    
    @QtCore.pyqtSlot()
    def openUploadForm(self):
        modDir = QtGui.QFileDialog.getExistingDirectory(self.client, "Select the mod directory to upload", MODFOLDER,  QtGui.QFileDialog.ShowDirsOnly)
        logger.debug("Uploading mod from: " + modDir)
        if modDir != "":
            if isModFolderValid(modDir):
                #os.chmod(modDir, S_IWRITE) Don't need this at the moment
                modinfofile, modinfo = parseModInfo(modDir)
                if modinfofile.error:
                    logger.debug("There were " + str(modinfofile.errors) + " errors and " + str(modinfofile.warnings) + " warnings.")
                    logger.debug(modinfofile.errorMsg)
                    QtGui.QMessageBox.critical(self.client, "Lua parsing error", modinfofile.errorMsg + "\nMod uploading cancelled.")
                else:
                    if modinfofile.warning:
                        uploadmod = QtGui.QMessageBox.question(self.client, "Lua parsing warning", modinfofile.errorMsg + "\nDo you want to upload the mod?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
                    else:
                        uploadmod = QtGui.QMessageBox.Yes
                    if uploadmod == QtGui.QMessageBox.Yes:
                        modinfo = ModInfo(**modinfo)
                        modinfo.setFolder(os.path.split(modDir)[1])
                        modinfo.update()
                        dialog = UploadModWidget(self, modDir, modinfo)
                        dialog.exec_()
            else :
                QtGui.QMessageBox.information(self.client,"Mod selection",
                        "This folder doesn't contain a mod_info.lua file")

    @QtCore.pyqtSlot()
    def tabOpened(self):
        self.client.lobby_connection.send(dict(command="modvault",type="start"))

    def updateVisibilities(self):
        logger.debug("Updating visibilities with sort '%s' and visibility '%s'" % (self.sortType, self.showType))
        for mod in self.mods:
            self.mods[mod].updateVisibility()
        self.modList.sortItems(1)

    def downloadMod(self, mod):
        if downloadMod(mod):
            self.client.lobby_connection.send(dict(command="modvault",type="download", uid=mod.uid))
            self.uids = [mod.uid for mod in getInstalledMods()]
            self.updateVisibilities()
            return True
        else: return False

    def removeMod(self, mod):
        if removeMod(mod):
            self.uids = [m.uid for m in installedMods]
            mod.updateVisibility()
    
        

#the drawing helper function for the modlist
class ModItemDelegate(QtGui.QStyledItemDelegate):
    
    def __init__(self, *args, **kwargs):
        QtGui.QStyledItemDelegate.__init__(self, *args, **kwargs)
        
    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
                
        painter.save()
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        
        icon = QtGui.QIcon(option.icon)
        iconsize = icon.actualSize(option.rect.size())
        
        #clear icon and text before letting the control draw itself because we're rendering these parts ourselves
        option.icon = QtGui.QIcon()        
        option.text = ""  
        option.widget.style().drawControl(QtGui.QStyle.CE_ItemViewItem, option, painter, option.widget)
        
        #Shadow
        painter.fillRect(option.rect.left()+8-1, option.rect.top()+8-1, iconsize.width(), iconsize.height(), QtGui.QColor("#202020"))

        #Icon
        icon.paint(painter, option.rect.adjusted(5-2, -2, 0, 0), QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        
        #Frame around the icon
        pen = QtGui.QPen()
        pen.setWidth(1);
        pen.setBrush(QtGui.QColor("#303030"));  #FIXME: This needs to come from theme.
        pen.setCapStyle(QtCore.Qt.RoundCap);
        painter.setPen(pen)
        painter.drawRect(option.rect.left()+5-2, option.rect.top()+3, iconsize.width(), iconsize.height())

        #Description
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

class ModItem(QtGui.QListWidgetItem):
    TEXTWIDTH = 230
    ICONSIZE = 100
    PADDING = 10
    
    WIDTH = ICONSIZE + TEXTWIDTH
    #DATA_PLAYERS = 32
    
    
    FORMATTER_MOD = str(util.readfile("modvault/modinfo.qthtml"))
    FORMATTER_MOD_UI = str(util.readfile("modvault/modinfoui.qthtml"))
    
    def __init__(self, parent, uid, *args, **kwargs):
        QtGui.QListWidgetItem.__init__(self, *args, **kwargs)

        self.parent = parent
        self.uid = uid
        self.name = ""
        self.description = ""
        self.author = ""
        self.version = 0
        self.downloads = 0
        self.likes = 0
        self.played = 0
        self.comments = [] #every element is a dictionary with a 
        self.bugreports = [] #text, author and date key
        self.date = None
        self.isuidmod = False
        self.uploadedbyuser = False

        self.thumbnail = None
        self.link = ""
        self.loadThread = None
        self.setHidden(True)

    def update(self, dic):
        self.name = dic["name"]
        self.played = dic["played"]
        self.description = dic["description"]
        self.version = dic["version"]
        self.author = dic["author"]
        self.downloads = dic["downloads"]
        self.likes = dic["likes"]
        self.comments = dic["comments"]
        self.bugreports = dic["bugreports"]
        self.date = QtCore.QDateTime.fromTime_t(dic['date']).toString("yyyy-MM-dd")
        self.isuimod = dic["ui"]
        self.link = dic["link"] #Direct link to the zip file.
        self.thumbstr = dic["thumbnail"]# direct url to the thumbnail file.
        self.uploadedbyuser = (self.author == self.parent.client.login)

        self.thumbnail = None
        if self.thumbstr == "":
            self.setIcon(util.icon("games/unknown_map.png"))
        else:
            img = getIcon(os.path.basename(urllib.parse.unquote(self.thumbstr)))
            if img:
                self.setIcon(util.icon(img, False))
            else:
                self.parent.client.downloader.downloadModPreview(self.thumbstr, self)
        self.updateVisibility()

    def updateIcon(self):
        self.setIcon(self.thumbnail)

    def shouldBeVisible(self):
        p = self.parent
        if p.searchString != "":
            if not (self.author.lower().find(p.searchString) != -1 or self.name.lower().find(p.searchString) != -1 or self.description.lower().find(" " + p.searchString +" ") != -1):
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
        else: #shouldn't happen
            return True

    def updateVisibility(self):
        self.setHidden(not self.shouldBeVisible())
        if len(self.description) < 200:
            descr = self.description
        else:
            descr = self.description[:197] + "..."

        modtype = ""
        if self.isuimod: modtype ="UI mod"
        if self.uid in self.parent.uids: color="green"
        else: color="white"
        
        if self.isuimod:
            self.setText(self.FORMATTER_MOD_UI.format(color=color,version=str(self.version),title=self.name,
                description=descr, author=self.author,downloads=str(self.downloads),
                likes=str(self.likes),date=str(self.date),modtype=modtype))
        else:
            self.setText(self.FORMATTER_MOD.format(color=color,version=str(self.version),title=self.name,
                description=descr, author=self.author,downloads=str(self.downloads),
                likes=str(self.likes),date=str(self.date),modtype=modtype,played=str(self.played)))

        self.setToolTip('<p width="230">%s</p>' % self.description)

    def __ge__(self, other):
        return not self.__lt__(self, other)

    def __lt__(self, other):
        if self.parent.sortType == "alphabetical":
            if self.name.lower() == other.name.lower():
                return (self.uid < other.uid)
            return (self.name.lower() > other.name.lower())
        elif self.parent.sortType == "rating":
            if self.likes == other.likes:
                return (self.downloads < other.downloads)
            return (self.likes < other.likes)
        elif self.parent.sortType == "downloads":
            if self.downloads == other.downloads:
                return (self.date < other.date)
            return (self.downloads < other.downloads)
        elif self.parent.sortType == "date":
            if self.date == other.date:
                return (self.name.lower() < other.name.lower())
            return (self.date < other.date)

