
import os

from PyQt5 import QtCore, QtGui, QtWidgets

import downloadManager
import util
from fa import maps
from mapGenerator import mapgenUtils

FormClass, BaseClass = util.THEME.loadUiType("vault/map.ui")

class MapWidget(FormClass, BaseClass):
    ICONSIZE = QtCore.QSize(256, 256)

    def __init__(self, parent, _map, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)

        self.setupUi(self)
        self.parent = parent

        util.THEME.stylesheets_reloaded.connect(self.load_stylesheet)
        self.load_stylesheet()

        self.setWindowTitle(_map.name)

        self._map = _map

        self.Title.setText(_map.name)
        self.Description.setText(_map.description)
        maptext = ""
        if _map.unranked: maptext = "Unranked map\n"
        self.Info.setText(maptext + "Uploaded %s" % (str(_map.date)))
        self.Players.setText("Maximum players: " + str(_map.maxPlayers))
        self.Size.setText("Size: " + str(_map.width) + " x " + str(_map.height) + " km")
        self.map_downloader = downloadManager.PreviewDownloader(util.MAP_PREVIEW_SMALL_DIR, util.MAP_PREVIEW_LARGE_DIR,
                                                                downloadManager.MAP_PREVIEW_ROOT)
        self._map_dl_request = downloadManager.DownloadRequest()
        self._map_dl_request.done.connect(self._on_preview_downloaded)

        #ensure that pixmap is set
        self.Picture.setPixmap(util.THEME.pixmap("games/unknown_map.png"))
        self.updatePreview()

        if maps.isBase(self._map.folderName):
            self.DownloadButton.setText("This is a base map")
            self.DownloadButton.setEnabled(False)
        elif mapgenUtils.isGeneratedMap(self._map.folderName):
            self.DownloadButton.setEnabled(False)
        elif maps.isMapAvailable(self._map.folderName):
            self.DownloadButton.setText("Remove Map")

        self.DownloadButton.clicked.connect(self.download)

    def load_stylesheet(self):
        self.setStyleSheet(util.THEME.readstylesheet("client/client.css"))

    @QtCore.pyqtSlot()
    def download(self):
        if not maps.isMapAvailable(self._map.folderName):
            self.parent.downloadMap(self._map.link)
            self.done(1)
        else:
            show = QtWidgets.QMessageBox.question(self.parent.client, "Delete Map",
                                                  "Are you sure you want to delete this map?",
                                                  QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
            if show == QtWidgets.QMessageBox.Yes:
                self.parent.removeMap(self._map.folderName)
                self.done(1)

    def updatePreview(self):
        imgPath = os.path.join(util.MAP_PREVIEW_LARGE_DIR, self._map.folderName + ".png")
        if os.path.isfile(imgPath):
            pix = QtGui.QPixmap(imgPath).scaled(self.ICONSIZE)
            self.Picture.setPixmap(pix)
        elif mapgenUtils.isGeneratedMap(self._map.folderName):
            self.Picture.setPixmap(util.THEME.pixmap("games/generated_map.png"))
        else:
            self.map_downloader.download_preview(self._map.folderName, self._map_dl_request, 
                                                        url = self._map.thumbnailLarge, large = True)

    def _on_preview_downloaded(self, mapname, result):
        filename, themed = result
        pixmap = util.THEME.pixmap(filename, themed)
        if themed:
            self.Picture.setPixmap(pixmap)
        else:
            self.Picture.setPixmap(pixmap.scaled(self.ICONSIZE))
