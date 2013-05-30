#-------------------------------------------------------------------------------
# Copyright (c) 2012 Gael Honorez.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#-------------------------------------------------------------------------------

"""
Modvault database documentation:
command = "mapvault"
possible commands:
    start: <no args>
    download_inc: uid
    addcomment: {"name","uid","date","text"}
    addbugreport: {"name","uid","date","text"}


Can also send a UPLOAD_MOD command directly using writeToServer
"UPLOAD_MOD","modname.zip",{mod info}, qfile
"""

import os
import datetime
import zipfile

from PyQt4 import QtCore, QtGui

import util
import logging
from vault import luaparser
from modwidget import ModWidget
from uploadwidget import UploadModWidget

logger = logging.getLogger("faf.modvault")
logger.setLevel(logging.DEBUG)

dateDummy = datetime.datetime(2013,5,27)

def strtodate(s):
    return dateDummy.strptime(s,"%Y-%m-%d %H:%M:%S")
def datetostr(d):
    return str(d)[:-7]
def now():
    return dateDummy.now()

MODFOLDER = os.path.join(util.PERSONAL_DIR, "My Games", "Gas Powered Games", "Supreme Commander Forged Alliance", "Mods")
MODVAULT_DOWNLOAD_ROOT = "http://www.faforever.com/faf/modvault/"

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

        self.SortType.currentIndexChanged.connect(self.sortChanged)
        self.ShowType.currentIndexChanged.connect(self.showChanged)
        self.toggleUIButton.toggled.connect(self.toggleUI)
        self.toggleBigButton.toggled.connect(self.toggleBig)
        self.toggleSmallButton.toggled.connect(self.toggleSmall)
        self.toggleYoursButton.toggled.connect(self.toggleYours)

        self.client.showMods.connect(self.tabOpened)
        self.client.modvaultInfo.connect(self.modInfo)

        self.sortType = "alphabetical"
        self.showType = "all"
        self.searchString = ""

        self.mods = []
        self.installedMods = self.getInstalledMods()

    @QtCore.pyqtSlot(dict)
    def modInfo(self, message): #this is called when the database has send a mod to us
        """
        message should have the following keys:
        
        """
        uid = message["uid"]
        mod = ModItem(self, uid)
        mod.update(message)
        self.mods.append(mod)

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
            self.showType = "big"
        elif index == 3:
            self.showType = "small"
        elif index == 4:
            self.showType = "yours"
        self.updateVisibilities()
    

    @QtCore.pyqtSlot(QtGui.QListWidgetItem)
    def modClicked(self, item):
        widget = ModWidget(self, item)
        widget.exec_()

    @QtCore.pyqtSlot()
    def search(self):
        self.searchString = searchInput.text().lower()
        self.updateVisibilities()
    
    @QtCore.pyqtSlot()
    def openUploadForm(self):
        modDir = QtGui.QFileDialog.getExistingDirectory(self.client, "Select the mod directory to upload", MODFOLDER,  QtGui.QFileDialog.ShowDirsOnly)
        logger.debug("Uploading mod from: " + modDir)
        if modDir != "":
            if isModFolderValid(modDir):
                os.chmod(mapDir, S_IWRITE)
                modinfofile = luaparser.luaParser(os.path.join(modDir,"mod_info.lua"))
                modinfo = modinfofile.parse({"name":"name","uid":"uid","version":"version","description":"description","ui_only":"ui_only"},
                                            {"version":1,"ui_only":"false","description":""})
                
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
                        modinfo["author"] = self.client.login
                        dialog = UploadModWidget(self, modDir, modinfo)
                        dialog._exec()
            else :
                QtGui.QMessageBox.information(self.client,"Mod selection",
                        "This folder doesn't contain a mod_info.lua file")

    @QtCorwe.pyqtSlot()
    def tabOpened(self):
        self.client.send(dict(command="modvault",type="start"))

    def updateVisibilities(self):
        for mod in mods:
            mod.updateVisibility()

    def getInstalledMods(self): #returns a list of names of installed mods
        mods = []
        if os.path.isdir(MODFOLDER) :
            mods = os.listdir(MODFOLDER)
        return mods

    def downloadMod(self, mod): #most of this function is stolen from maps.downloadMap
        link = mod.link
        url = MODVAULT_DOWNLOAD_ROOT + link
        logger.debug("Getting mod from: " + url)

        progress = QtGui.QProgressDialog()
        progress.setCancelButtonText("Cancel")
        progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        
        try:
            zipwebfile  = urllib2.urlopen(url)
            meta = zipwebfile.info()
            file_size = int(meta.getheaders("Content-Length")[0])

            progress.setMinimum(0)
            progress.setMaximum(file_size)
            progress.setModal(1)
            progress.setWindowTitle("Downloading Map")
            progress.setLabelText(name)
        
            progress.show()
        
            #Download the file as a series of 8 KiB chunks, then uncompress it.
            output = cStringIO.StringIO()
            file_size_dl = 0
            block_sz = 8192       

            while progress.isVisible():
                read_buffer = zipwebfile.read(block_sz)
                if not read_buffer:
                    break
                file_size_dl += len(read_buffer)
                output.write(read_buffer)
                progress.setValue(file_size_dl)
        
            progress.close()
            
            if file_size_dl == file_size:
                zfile = zipfile.ZipFile(output)
                zfile.extractall(MODFOLDER)
                logger.debug("Successfully downloaded and extracted mod from: " + url)
            else:    
                logger.warn("Mod download cancelled for: " + url)        
                return False

        except:
            logger.warn("Mod download or extraction failed for: " + url)        
            if sys.exc_type is HTTPError:
                logger.warning("ModVault download failed with HTTPError, mod probably not in vault (or broken).")
                QtGui.QMessageBox.information(None, "Mod not downloadable", "<b>This mod was not found in the vault (or is broken).</b><br/>You need to get it from somewhere else in order to use it." )
            else:                
                logger.error("Download Exception", exc_info=sys.exc_info())
                QtGui.QMessageBox.information(None, "Mod installation failed", "<b>This mod could not be installed (please report this map or bug).</b>")
            return False

        #Count the map downloads
        self.client.send(dict(command="modvault", type="download_inc", uid=mod.uid))
        self.installedMods.append(mod.name)
        return True
        

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
        painter.drawRect(option.rect.left()+5-2, option.rect.top()+5-2, iconsize.width(), iconsize.height())

        #Description
        painter.translate(option.rect.left() + iconsize.width() + 10, option.rect.top()+10)
        clip = QtCore.QRectF(0, 0, option.rect.width()-iconsize.width() - 10 - 5, option.rect.height())
        html.drawContents(painter, clip)
  
        painter.restore()
        

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        html.setTextWidth(ModItem.TEXTWIDTH)
        return QtCore.QSize(ModItem.ICONSIZE + ModItem.TEXTWIDTH + ModItem.PADDING, ModItem.ICONSIZE)  


class ModItem(QtGui.QListWidgetItem):
    TEXTWIDTH = 230
    ICONSIZE = 100
    PADDING = 10
    
    WIDTH = ICONSIZE + TEXTWIDTH
    #DATA_PLAYERS = 32
    
    
    FORMATTER_MOD = unicode(util.readfile("modvault/modinfo.qthtml"))
    
    def __init__(self, parent, uid, *args, **kwargs):
        QtGui.QListWidgetItem.__init__(self, *args, **kwargs)

        self.parent = parent
        self.uid = uid
        self.title = ""
        self.description = ""
        self.author = ""
        self.downloads = 0
        self.likes = 0
        self.comments = [] #every element is a dictionary with a 
        self.bugreports = [] #text, author and date key
        self.date = None
        self.isuidmod = False
        self.isbigmod = False
        self.issmallmod = False
        self.uploadedbyuser = False

        self.thumbnail = None
        self.link = ""
        self.setHidden(True)

    def update(self, dic):
        self.title = dic["title"]
        self.description = dic["description"]
        self.author = dic["author"]
        self.downloads = dic["downloads"]
        self.likes = dic["likes"]
        self.comments = dic["comments"]
        self.bugreports = dic["bugreports"]
        self.date = strtodate(dic["date"])
        self.last_updated = strtodate(dic["last_updated"])
        self.isuimod = dic["ui"]
        self.isbigmod = dic["big"]
        self.issmallmod = dic["small"]
        self.link = dic["link"] #Direct link to the zip file.
        self.thumbnail = dic["tumbnail"] # should be a thing that can be passed to setIcon or None
        self.uploadedbyuser = (self.author == self.parent.client.login)

        if self.thumbnail == None:
            self.setIcon(util.icon("games/unknown_map.png"))
        else:
            self.setIcon(self.tumbnail)

        if len(self.description) < 200:
            descr = self.description
        else:
            descr = self.description[:197] + "..."
        
        if self.title in self.parent.installedMods: color="green"
        else: color="white"
        self.setText(self.FORMATTER_MOD.format(color=color,title=self.title,
            description=descr, author=self.author,downloads=str(self.downloads),
            likes=str(self.likes),date=str(self.date.date())))

        self.setToolTip('<p width="230">%s</p>' % self.description)
        self.setHidden(self.shouldBeVisible())

    def shouldBeVisible(self):
        p = self.parent
        if p.searchString != "":
            if not (self.author.lower().find(p.searchString) != -1 or  self.title.lower().find(p.searchString) != -1):
                return False
        if p.showType == "all":
            return True
        if p.showType == "ui":
            return self.isuimod
        if p.showTYpe == "big":
            return self.isbigmod
        if p.showType == "small":
            return self.issmallmod
        if p.showType == "yours":
            return self.uploadedbyuser
        else: #shouldn't happen
            return True

    def __ge__(self, other):
        return not self.__lt__(self, other)

    def __lt__(self, other):
        if self.parent.sortType == "alphabetic":
            if self.title.lower() == other.title.lower():
                return (self.uid < other.uid)
            return (self.title.lower() > other.title.lower())
        elif self.parent.sortType == "rating":
            if self.rating == other.rating:
                return (self.downloads < other.downloads)
            return (self.rating < other.rating)
        elif self.parent.sortType == "downloads":
            if self.downloads == other.downloads:
                return (self.date < other.date)
            return (self.downloads < other.downloads)
        elif self.parent.sortType == "date":
            if self.date == other.date:
                return (self.title.lower() < other.title.lower())
            return (self.date < other.date)
        
def modToFilename(mod):
    return os.path.join(MODFOLDER, mod.name)

def isModFolderValid(folder):
    return os.path.exists(os.path.join(folder,"mod_info.lua"))
