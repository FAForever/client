# system imports
import logging
import sys
from PyQt5 import QtCore, QtGui, QtWidgets, QtNetwork
import os
import re
import shutil
import random

# local imports
from config import Settings
import fafpath
from vault.dialogs import downloadFile
from mapGenerator.mapgenProcess import MapGeneratorProcess
from mapGenerator.mapgenUtils import isGeneratedMap, versionPattern, generatedMapPattern
from fa.maps import getUserMapsFolder
import util

logger = logging.getLogger(__name__)

releaseUrl = "https://github.com/FAForever/Neroxis-Map-Generator/releases/"
generatorJarName = "MapGenerator_{}.jar"


class MapGeneratorManager(object):
    def __init__(self):
        self.latestVersion = None
        self.response = None

        self.currentVersion = Settings.get('mapGenerator/version', "0", str)

    def generateMap(self, mapname=None, args=None):
        if mapname is None:
            '''
             Requests latest version once per session
            '''
            if self.currentVersion == "0" or not self.latestVersion:
                self.checkUpdates()

                if self.latestVersion and self.versionController(self.latestVersion):
                    self.currentVersion = self.latestVersion   # mapgen is up-to-date
                    Settings.set('mapGenerator/version', self.currentVersion)
                elif self.currentVersion == "0":               # if not "0", use older version
                    return False                               # otherwise we don't have any generator at all
            version = self.currentVersion
            args = args
        else:
            matcher = generatedMapPattern.match(mapname)
            version = matcher.group(1)
            seed = matcher.group(2) #not used here because often it is not numeric
            args = ['--map-name', mapname]
        
        actualPath = self.versionController(version)

        if actualPath:
            auto = Settings.get('mapGenerator/autostart', default=False, type=bool)
            if not auto and mapname is not None:
                msgbox = QtWidgets.QMessageBox()
                msgbox.setWindowTitle("Generate map")
                msgbox.setText("It looks like you don't have the map being used by this lobby. Do you want to generate it? <br/><b>" + mapname + "</b>")
                msgbox.setInformativeText("Map generation is a CPU intensive task and may take some time.")
                msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.YesToAll | QtWidgets.QMessageBox.No)
                result = msgbox.exec_()
                if result == QtWidgets.QMessageBox.No:
                    return False
                elif result == QtWidgets.QMessageBox.YesToAll:
                    Settings.set('mapGenerator/autostart', True)
            
            mapsFolder = getUserMapsFolder()
            if not os.path.exists(mapsFolder):
                os.makedirs(mapsFolder)

            # Start generator with progress bar
            self.generatorProcess = MapGeneratorProcess(actualPath, mapsFolder, args)
            
            map_ = self.generatorProcess.mapname
            # Check if map exists or generator failed
            if os.path.isdir(os.path.join(mapsFolder, map_)):
                return map_
            else:
                return False
        else:
            return False
            
    def generateRandomMap(self):
        ''' 
        Called when user click "generate map" in host widget.
        Prepares seed and requests latest version once per session
        '''

        if self.currentVersion == "0" or not self.latestVersion:
            self.checkUpdates()

            if self.latestVersion and self.versionController(self.latestVersion):
                self.currentVersion = self.latestVersion   # mapgen is up-to-date
                Settings.set('mapGenerator/version', self.currentVersion)
            elif self.currentVersion == "0":               # if not "0", use older version
                return False                               # otherwise we don't have any generator at all

        seed = random.randint(-9223372036854775808, 9223372036854775807)
        mapName = "neroxis_map_generator_{}_{}".format(self.currentVersion, seed)

        return self.generateMap(mapName)
   
    def versionController(self, version):
        name = generatorJarName.format(version)
        filePath = os.path.join(util.MAPGEN_DIR, name)
        
        # Check if required version is already in folder
        if os.path.isdir(util.MAPGEN_DIR):
            for infile in os.listdir(util.MAPGEN_DIR):
                if infile.lower() == name.lower():
                    return filePath

        # Download from github if not            
        url = releaseUrl + "download/{}/NeroxisGen_{}.jar".format(version,version)
        return downloadFile(url, filePath, name, "map generator", silent = False)

    def checkUpdates(self):
        '''
        Not downloading anything here.
        Just requesting latest version and return the number
        '''
        self.manager = QtNetwork.QNetworkAccessManager()
        self.manager.finished.connect(self.onRequestFinished)

        request = QtNetwork.QNetworkRequest(QtCore.QUrl(releaseUrl + "latest"))
        self.manager.get(request)
        
        progress = QtWidgets.QProgressDialog()
        progress.setCancelButtonText("Cancel")
        progress.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setMinimum(0)
        progress.setMaximum(0)
        progress.setValue(0)
        progress.setModal(1)
        progress.setWindowTitle("Looking for updates")
        progress.show()

        while not self.response:
            QtWidgets.QApplication.processEvents()
        progress.close()

    def onRequestFinished(self, reply):
        redirectUrl = reply.attribute(2)
        if redirectUrl:
            redirectUrl = redirectUrl.toString()
            if "releases/tag/" in redirectUrl:
                self.latestVersion = redirectUrl.rsplit('/', 1)[1]

        self.response = True