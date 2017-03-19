from PyQt5 import QtCore, QtWidgets, QtWebKitWidgets
from stat import *
import util
import urllib.request, urllib.parse, urllib.error
import logging
import os
from fa import maps
from vault import luaparser
import urllib.request, urllib.error, urllib.parse
import re
from config import Settings

logger = logging.getLogger(__name__)


class FAFPage(QtWebKitWidgets.QWebPage):
    def __init__(self):
        super(QtWebKitWidgets.QWebPage, self).__init__()

    def userAgentForUrl(self, url):
        return "FAForever"


class MapVault(QtCore.QObject):
    def __init__(self, client, *args, **kwargs):
        QtCore.QObject.__init__(self, *args, **kwargs)
        self.client = client

        logger.debug("Map Vault tab instantiating")

        self.ui = QtWebKitWidgets.QWebView()

        self.ui.setPage(FAFPage())

        self.ui.page().mainFrame().javaScriptWindowObjectCleared. \
            connect(self.addScript)

        self.client.mapsTab.layout().addWidget(self.ui)

        self.loaded = False
        self.client.showMaps.connect(self.reloadView)
        self.ui.loadFinished.connect(self.ui.show)
        self.reloadView()

    @QtCore.pyqtSlot()
    def reloadView(self):
        if self.loaded:
            return
        self.loaded = True

        self.ui.setVisible(False)

#       If a local theme CSS exists, skin the WebView with it
        if util.themeurl("vault/style.css"):
            self.ui.settings().setUserStyleSheetUrl(
                util.themeurl("vault/style.css"))

        ROOT = Settings.get('content/host')

        url = QtCore.QUrl(ROOT)
        url.setPath("/faf/vault/maps.php")
        query = QtCore.QUrlQuery(url.query())
        query.addQueryItem('username', self.client.login)
        query.addQueryItem('pwdhash', self.client.password)
        url.setQuery(query)

        self.ui.setUrl(url)

    @QtCore.pyqtSlot()
    def addScript(self):
        frame = self.ui.page().mainFrame()
        frame.addToJavaScriptWindowObject("webVault", self)

    def __preparePositions(self, positions, map_size):
        img_size = [256, 256]
        size = [int(map_size['0']), int(map_size['1'])]
        off_x = 0
        off_y = 0

        if size[1] > size[0]:
            img_size[0] = img_size[0]/2
            off_x = img_size[0]/2
        elif size[0] > size[1]:
            img_size[1] = img_size[1]/2
            off_y = img_size[1]/2

        cf_x = size[0]/img_size[0]
        cf_y = size[1]/img_size[1]

        regexp = re.compile(" \\d+\\.\\d*| \\d+")

        for postype in positions:
            for pos in positions[postype]:
                values = regexp.findall(positions[postype][pos])
                x = off_x + float(values[0].strip())/cf_x
                y = off_y + float(values[2].strip())/cf_y
                positions[postype][pos] = [int(x), int(y)]

    @QtCore.pyqtSlot()
    def uploadMap(self):
        mapDir = QtWidgets.QFileDialog.getExistingDirectory(
            self.client,
            "Select the map directory to upload",
            maps.getUserMapsFolder(),
            QtWidgets.QFileDialog.ShowDirsOnly)
        logger.debug("Uploading map from: " + mapDir)
        if mapDir != "":
            if maps.isMapFolderValid(mapDir):
                os.chmod(mapDir, S_IWRITE)
                mapName = os.path.basename(mapDir)
                zipName = mapName.lower()+".zip"

                scenariolua = luaparser.luaParser(os.path.join(
                    mapDir,
                    maps.getScenarioFile(mapDir)))
                scenarioInfos = scenariolua.parse({
                    'scenarioinfo>name':'name', 'size':'map_size',
                    'description':'description',
                    'count:armies':'max_players',
                    'map_version':'version',
                    'type':'map_type',
                    'teams>0>name':'battle_type'
                    }, {'version':'1'})

                if scenariolua.error:
                    logger.debug("There were {} errors and {} warnings".format(
                        scenariolua.errors,
                        scenariolua.warnings
                        ))
                    logger.debug(scenariolua.errorMsg)
                    QtWidgets.QMessageBox.critical(
                        self.client,
                        "Lua parsing error",
                        "{}\nMap uploading cancelled.".format(
                            scenariolua.errorMsg))
                else:
                    if scenariolua.warning:
                        uploadmap = QtWidgets.QMessageBox.question(
                            self.client,
                            "Lua parsing warning",
                            "{}\nDo you want to upload the map?".format(
                                scenariolua.errorMsg),
                            QtWidgets.QMessageBox.Yes,
                            QtWidgets.QMessageBox.No)
                    else:
                        uploadmap = QtWidgets.QMessageBox.Yes
                    if uploadmap == QtWidgets.QMessageBox.Yes:
                        savelua = luaparser.luaParser(os.path.join(
                            mapDir,
                            maps.getSaveFile(mapDir)
                            ))
                        saveInfos = savelua.parse({
                            'markers>mass*>position':'mass:__parent__',
                            'markers>hydro*>position':'hydro:__parent__',
                            'markers>army*>position':'army:__parent__'})
                        if savelua.error or savelua.warning:
                            logger.debug("There were {} errors and {} warnings".format(
                                scenariolua.errors,
                                scenariolua.warnings
                                ))
                            logger.debug(scenariolua.errorMsg)

                        self.__preparePositions(
                            saveInfos,
                            scenarioInfos["map_size"])

                        tmpFile = maps.processMapFolderForUpload(
                            mapDir,
                            saveInfos)
                        if not tmpFile:
                            QtWidgets.QMessageBox.critical(
                                self.client,
                                "Map uploading error",
                                "Couldn't make previews for {}\n"
                                "Map uploading cancelled.".format(mapName))
                            return None

                        qfile = QtCore.QFile(tmpFile.name)
                        self.client.lobby_connection.writeToServer("UPLOAD_MAP", zipName, scenarioInfos, qfile)

                        #removing temporary files
                        qfile.remove()
            else:
                QtWidgets.QMessageBox.information(
                    self.client,
                    "Map selection",
                    "This folder doesn't contain valid map data.")

    @QtCore.pyqtSlot(str)
    def downloadMap(self, link):
        link = urllib.parse.unquote(link)
        name = maps.link2name(link)
        if not maps.isMapAvailable(name):
            maps.downloadMap(name)
            maps.existMaps(True)
        else:
            show = QtWidgets.QMessageBox.question(
                self.client,
                "Already got the Map",
                "Seems like you already have that map!<br/><b>Would you like to see it?</b>",
                QtWidgets.QMessageBox.Yes,
                QtWidgets.QMessageBox.No)
            if show == QtWidgets.QMessageBox.Yes:
                util.showDirInFileBrowser(maps.folderForMap(name))
