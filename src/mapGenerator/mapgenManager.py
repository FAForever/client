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
from fa.maps import getUserMapsFolder

logger = logging.getLogger(__name__)

class MapGeneratorManager(object):
    def __init__(self):
        self.releaseUrl = "https://github.com/FAForever/Neroxis-Map-Generator/releases/download/{}/NeroxisGen_{}.jar"
        self.latestRelease = "https://github.com/FAForever/Neroxis-Map-Generator/releases/latest"
        self.latestVersion = None
        self.response = None

        self.currentVersion = Settings.get('mapGenerator/version', "0", str)
        self.previousMaps = Settings.get('mapGenerator/deleteMaps')
        self.generatorPath = os.path.join(fafpath.get_libdir(), "map-generator")
        self.mapsFolder = getUserMapsFolder()

        if self.previousMaps:
            self.deletePreviousMaps()

    def generateMap(self, mapname):
        dataString =  mapname.split("neroxis_map_generator",1)[1]
        version = re.search(r'\_(.*?)\_',dataString).group(1)
        seed = dataString.rsplit('_', 1)[1]

        actualPath = self.versionController(version)

        if actualPath:
            auto = Settings.get('mapGenerator/autostart', default=False, type=bool)
            if not auto:
                msgbox = QtWidgets.QMessageBox()
                msgbox.setWindowTitle("Generate map")
                msgbox.setText("Seems that you don't have the map used this game. Do you want to generate it?<br/><b>" + mapname + "</b>")
                msgbox.setInformativeText("Map generation is CPU intensive task and may take some time.")
                msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.YesToAll | QtWidgets.QMessageBox.No)
                result = msgbox.exec_()
                if result == QtWidgets.QMessageBox.No:
                    return False
                elif result == QtWidgets.QMessageBox.YesToAll:
                    Settings.set('mapGenerator/autostart', True)
            
            # Start generator with progress bar      
            self.generatorProcess = MapGeneratorProcess(actualPath, self.mapsFolder, seed, version, mapname)
            
            # Check if map exists or generator failed
            if os.path.isdir(os.path.join(self.mapsFolder, mapname)):
                if self.previousMaps:
                    self.previousMaps = self.previousMaps + ";" + mapname
                else:
                    self.previousMaps = mapname
                Settings.set('mapGenerator/deleteMaps', self.previousMaps)
                
                return mapname
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

        seed = ''.join(["%s" % random.randint(0, 9) for num in range(0, 19)])
        mapName = "neroxis_map_generator_{}_{}".format(self.currentVersion, seed)

        return self.generateMap(mapName)
   
    def versionController(self, version):
        name = "NeroxisGen_{}.jar".format(version)
        filePath = self.generatorPath + "\\" + name
        
        # Check if required version is already in folder
        if os.path.isdir(self.generatorPath):
            for infile in os.listdir(self.generatorPath):
                if infile.lower() == name.lower():
                    return filePath

        # Download from github if not            
        url = self.releaseUrl.format(version,version)
        return downloadFile(url, filePath, name, "map generator", silent = False)
 
    def deletePreviousMaps(self):
        '''Delete maps that were created at previous session'''
        try:
            maps = self.previousMaps.split(";")
            for map in maps:
                if "neroxis_map_generator" in map: #just in case
                    mapPath = (os.path.join(self.mapsFolder, map))
                    if os.path.isdir(mapPath):
                        shutil.rmtree(os.path.join(mapPath), ignore_errors=True)
        except ValueError as e:
            logger.error("Error deleting maps created by map generator")
            logger.error(e)

        self.previousMaps = None
        Settings.set('mapGenerator/deleteMaps', self.previousMaps)
        
    def checkUpdates(self):
        '''
        Not downloading anything here.
        Just requesting latest version and return the number
        '''
        self.manager = QtNetwork.QNetworkAccessManager()
        self.manager.finished.connect(self.onRequestFinished)

        request = QtNetwork.QNetworkRequest(QtCore.QUrl(self.latestRelease))
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