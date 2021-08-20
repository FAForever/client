import logging
import os
import shutil
import urllib.error
import urllib.parse
import urllib.request
from stat import S_IWRITE

from PyQt5 import QtCore, QtGui, QtWidgets

import util
from api.vaults_api import MapApiConnector, MapPoolApiConnector
from downloadManager import DownloadRequest
from fa import maps
from mapGenerator import mapgenUtils
from ui.busy_widget import BusyWidget
from vault import luaparser

from .mapwidget import MapWidget

logger = logging.getLogger(__name__)


FormClass, BaseClass = util.THEME.loadUiType("vault/mapvault.ui")


class MapVault(FormClass, BaseClass, BusyWidget):
    def __init__(self, client, *args, **kwargs):
        QtCore.QObject.__init__(self, *args, **kwargs)
        self.client = client
        logger.debug("Map Vault tab instantiating")

        self.setupUi(self)

        self.loaded = True

        self.mapList.setItemDelegate(MapItemDelegate(self))
        self.mapList.itemDoubleClicked.connect(self.mapClicked)
        self.searchButton.clicked.connect(self.search)
        self.searchInput.returnPressed.connect(self.search)
        self.uploadButton.clicked.connect(self.uploadMap)

        self.SortType.setCurrentIndex(0)
        self.SortType.currentIndexChanged.connect(self.sortChanged)
        self.ShowType.currentIndexChanged.connect(self.showChanged)

        self.client.lobby_info.mapVaultInfo.connect(self.mapInfo)
        self.client.lobby_info.vaultMeta.connect(self.metaInfo)

        self.sortType = "alphabetical"
        self.showType = "all"
        self.searchString = ""
        self.searchQuery = dict(include='latestVersion,reviewsSummary')

        self.pageSize = self.quantityBox.value()
        self.pageNumber = 1

        self.goToPageButton.clicked.connect(
            lambda: self.goToPage(self.pageBox.value()),
        )
        self.pageBox.setValue(self.pageNumber)
        self.pageBox.valueChanged.connect(self.checkTotalPages)
        self.totalPages = None
        self.totalRecords = None
        self.quantityBox.valueChanged.connect(self.checkPageSize)
        self.nextButton.clicked.connect(
            lambda: self.goToPage(self.pageBox.value() + 1),
        )
        self.previousButton.clicked.connect(
            lambda: self.goToPage(self.pageBox.value() - 1),
        )
        self.firstButton.clicked.connect(lambda: self.goToPage(1))
        self.lastButton.clicked.connect(
            lambda: self.goToPage(self.totalPages),
        )
        self.resetButton.clicked.connect(self.resetSearch)

        self._maps = {}
        self.installed_maps = maps.getUserMaps()

        self.mapApiConnector = MapApiConnector(self.client.lobby_dispatch)
        self.mapPoolApiConnector = MapPoolApiConnector(
            self.client.lobby_dispatch,
        )

        self.apiConnector = self.mapApiConnector
        self.busy_entered()

        self.client.authorized.connect(self.busy_entered)

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
        self._maps.clear()
        self.mapList.clear()
        self.pageBox.setValue(page)
        self.pageNumber = self.pageBox.value()
        self.pageBox.setValue(self.pageNumber)
        self.updateQuery(self.pageNumber)
        self.apiConnector.requestData(self.searchQuery)
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
        self.apiConnector = self.mapApiConnector
        self.searchString = ''
        self.searchInput.clear()
        self.searchQuery = dict(include='latestVersion,reviewsSummary')
        self.goToPage(1)

    @QtCore.pyqtSlot(dict)
    def mapInfo(self, message):
        for value in message["values"]:
            folderName = value["folderName"]
            if folderName not in self._maps:
                _map = MapItem(self, folderName)
                self._maps[folderName] = _map
                self.mapList.addItem(_map)
            else:
                _map = self._maps[folderName]
            _map.update(value)
        self.mapList.sortItems(1)

    @QtCore.pyqtSlot(int)
    def sortChanged(self, index):
        if index == -1 or index == 0:
            self.sortType = "alphabetical"
        elif index == 1:
            self.sortType = "date"
        elif index == 2:
            self.sortType = "rating"
        elif index == 3:
            self.sortType = "size"
        self.updateVisibilities()

    @QtCore.pyqtSlot(int)
    def showChanged(self, index):
        if index == -1 or index == 0:
            self.showType = "all"
        elif index == 1:
            self.showType = "unranked"
        elif index == 2:
            self.showType = "ranked"
        elif index == 3:
            self.showType = "installed"
        self.updateVisibilities()

    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem)
    def mapClicked(self, item):
        widget = MapWidget(self, item)
        widget.exec_()

    def search(self):
        """ Sending search to mod server"""
        self.searchString = self.searchInput.text().lower()
        if self.searchString == '' or self.searchString.replace(' ', '') == '':
            self.resetSearch()
        else:
            self.apiConnector = self.mapApiConnector
            self.searchString = self.searchString.strip()
            self.searchQuery = dict(
                include='latestVersion,reviewsSummary',
                filter='displayName=="*{}*"'.format(self.searchString),
            )
            self.goToPage(1)

    def requestMapPool(self, queueName, minRating):
        self.apiConnector = MapPoolApiConnector(self.client.lobby_dispatch)
        self.searchQuery = dict(
            include=(
                'mapVersion,mapVersion.map.latestVersion,'
                'mapVersion.reviewsSummary'
            ),
            filter=(
                'mapPool.matchmakerQueueMapPool.matchmakerQueue.'
                'technicalName=="{}";'
                '(mapPool.matchmakerQueueMapPool.minRating=le="{}",'
                'mapPool.matchmakerQueueMapPool.minRating=isnull="true")'
                .format(queueName, minRating)
            ),
        )
        self.goToPage(1)

    @QtCore.pyqtSlot()
    def busy_entered(self):
        if not self._maps:
            self.goToPage(self.pageNumber)

    def updateVisibilities(self):
        logger.debug(
            "Updating visibilities with sort '{}' and visibility '{}'"
            .format(self.sortType, self.showType),
        )
        for _map in self._maps:
            self._maps[_map].updateVisibility()
        self.mapList.sortItems(1)

    @QtCore.pyqtSlot()
    def uploadMap(self):
        mapDir = QtWidgets.QFileDialog.getExistingDirectory(
            self.client,
            "Select the map directory to upload",
            maps.getUserMapsFolder(),
            QtWidgets.QFileDialog.ShowDirsOnly,
        )
        logger.debug("Uploading map from: " + mapDir)
        if mapDir != "":
            if maps.isMapFolderValid(mapDir):
                os.chmod(mapDir, S_IWRITE)
                mapName = os.path.basename(mapDir)
                # zipName = mapName.lower() + ".zip"

                scenariolua = luaparser.luaParser(
                    os.path.join(mapDir, maps.getScenarioFile(mapDir)),
                )
                scenarioInfos = scenariolua.parse(
                    {
                        'scenarioinfo>name': 'name',
                        'size': 'map_size',
                        'description': 'description',
                        'count:armies': 'max_players',
                        'map_version': 'version',
                        'type': 'map_type',
                        'teams>0>name': 'battle_type',
                    },
                    {'version': '1'},
                )

                if scenariolua.error:
                    logger.debug(
                        "There were {} errors and {} warnings".format(
                            scenariolua.errors,
                            scenariolua.warnings,
                        ),
                    )
                    logger.debug(scenariolua.errorMsg)
                    QtWidgets.QMessageBox.critical(
                        self.client,
                        "Lua parsing error",
                        (
                            "{}\nMap uploading cancelled."
                            .format(scenariolua.errorMsg)
                        ),
                    )
                else:
                    if scenariolua.warning:
                        uploadmap = QtWidgets.QMessageBox.question(
                            self.client,
                            "Lua parsing warning",
                            (
                                "{}\nDo you want to upload the map?"
                                .format(scenariolua.errorMsg)
                            ),
                            QtWidgets.QMessageBox.Yes,
                            QtWidgets.QMessageBox.No,
                        )
                    else:
                        uploadmap = QtWidgets.QMessageBox.Yes
                    if uploadmap == QtWidgets.QMessageBox.Yes:
                        savelua = luaparser.luaParser(
                            os.path.join(mapDir, maps.getSaveFile(mapDir)),
                        )
                        saveInfos = savelua.parse({
                            'markers>mass*>position': 'mass:__parent__',
                            'markers>hydro*>position': 'hydro:__parent__',
                            'markers>army*>position': 'army:__parent__',
                        })
                        if savelua.error or savelua.warning:
                            logger.debug(
                                "There were {} errors and {} warnings"
                                .format(
                                    scenariolua.errors,
                                    scenariolua.warnings,
                                ),
                            )
                            logger.debug(scenariolua.errorMsg)

                        self.__preparePositions(
                            saveInfos,
                            scenarioInfos["map_size"],
                        )

                        tmpFile = maps.processMapFolderForUpload(
                            mapDir,
                            saveInfos,
                        )
                        if not tmpFile:
                            QtWidgets.QMessageBox.critical(
                                self.client,
                                "Map uploading error",
                                (
                                    "Couldn't make previews for {}\n"
                                    "Map uploading cancelled.".format(mapName)
                                ),
                            )
                            return None

                        qfile = QtCore.QFile(tmpFile.name)

                        # TODO: implement uploading via API
                        ...
                        # removing temporary files
                        qfile.remove()
            else:
                QtWidgets.QMessageBox.information(
                    self.client,
                    "Map selection",
                    "This folder doesn't contain valid map data.",
                )

    @QtCore.pyqtSlot(str)
    def downloadMap(self, link):
        link = urllib.parse.unquote(link)
        name = maps.link2name(link)
        alt_name = name.replace(" ", "_")
        avail_name = None
        if maps.isMapAvailable(name):
            avail_name = name
        elif maps.isMapAvailable(alt_name):
            avail_name = alt_name
        if avail_name is None:
            maps.downloadMap(name)
            self.installed_maps.append(name)
            self.updateVisibilities()
        else:
            show = QtWidgets.QMessageBox.question(
                self.client,
                "Already got the Map",
                (
                    "Seems like you already have that map!<br/><b>Would you "
                    "like to see it?</b>"
                ),
                QtWidgets.QMessageBox.Yes,
                QtWidgets.QMessageBox.No,
            )
            if show == QtWidgets.QMessageBox.Yes:
                util.showDirInFileBrowser(maps.folderForMap(avail_name))

    @QtCore.pyqtSlot(str)
    def removeMap(self, folder):
        maps_folder = os.path.join(maps.getUserMapsFolder(), folder)
        if os.path.exists(maps_folder):
            shutil.rmtree(maps_folder)
            self.installed_maps.remove(folder)
            self.updateVisibilities()


class MapItemDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, *args, **kwargs):
        QtWidgets.QStyledItemDelegate.__init__(self, *args, **kwargs)

    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)

        painter.save()

        html = QtGui.QTextDocument()
        html.setHtml(option.text)

        icon = QtGui.QIcon(option.icon)
        iconsize = QtCore.QSize(MapItem.ICONSIZE, MapItem.ICONSIZE)

        # clear icon and text before letting the control draw itself because
        # we're rendering these parts ourselves
        option.icon = QtGui.QIcon()
        option.text = ""
        option.widget.style().drawControl(
            QtWidgets.QStyle.CE_ItemViewItem, option, painter, option.widget,
        )

        # Shadow
        painter.fillRect(
            option.rect.left() + 7, option.rect.top() + 7,
            iconsize.width(), iconsize.height(), QtGui.QColor("#202020"),
        )

        iconrect = QtCore.QRect(option.rect.adjusted(3, 3, 0, 0))
        iconrect.setSize(iconsize)
        # Icon
        icon.paint(
            painter, iconrect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
        )

        # Frame around the icon
        pen = QtGui.QPen()
        pen.setWidth(1)
        # FIXME: This needs to come from theme.
        pen.setBrush(QtGui.QColor("#303030"))

        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawRect(iconrect)

        # Description
        painter.translate(
            option.rect.left() + iconsize.width() + 10, option.rect.top() + 4,
        )
        clip = QtCore.QRectF(
            0, 0, option.rect.width() - iconsize.width() - 15,
            option.rect.height(),
        )
        html.drawContents(painter, clip)

        painter.restore()

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)

        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        html.setTextWidth(MapItem.TEXTWIDTH)
        return QtCore.QSize(
            MapItem.ICONSIZE
            + MapItem.TEXTWIDTH
            + MapItem.PADDING,
            MapItem.ICONSIZE + MapItem.PADDING,
        )


class MapItem(QtWidgets.QListWidgetItem):
    TEXTWIDTH = 230
    ICONSIZE = 100
    PADDING = 10

    WIDTH = ICONSIZE + TEXTWIDTH
    # DATA_PLAYERS = 32

    FORMATTER_MAP = str(util.THEME.readfile("vault/mapinfo.qthtml"))
    # FORMATTER_MAP_UI = str(util.THEME.readfile("vault/mapnfoui.qthtml"))

    def __init__(self, parent, folderName, *args, **kwargs):
        QtWidgets.QListWidgetItem.__init__(self, *args, **kwargs)

        self.parent = parent
        self.folderName = folderName
        self.name = ""
        self.description = ""
        self.version = 0
        self.rating = 0
        self.reviews = 0
        self.date = None
        self.height = 0
        self.width = 0

        self.thumbnail = None
        self.link = ""
        self.setHidden(True)

        self._map_dl_request = DownloadRequest()
        self._map_dl_request.done.connect(self._on_map_downloaded)

    def update(self, dic):
        self.name = maps.getDisplayName(dic["folderName"])
        self.description = dic["description"]
        self.version = dic["version"]
        self.maxPlayers = dic["maxPlayers"]
        self.rating = dic["rating"]
        self.reviews = dic["reviews"]

        # in km 51.2 pixels (or w/e) per km
        self.height = int(dic["height"] / 51.2)
        self.width = int(dic["width"] / 51.2)

        self.folderName = dic["folderName"]
        self.date = dic['date'][:10]
        self.unranked = not dic["ranked"]
        self.link = dic["link"]  # Direct link to the zip file.
        self.thumbstrSmall = dic["thumbnailSmall"]
        self.thumbnailLarge = dic["thumbnailLarge"]

        self.thumbnail = maps.preview(self.folderName)
        if self.thumbnail:
            self.setIcon(self.thumbnail)
        else:
            if self.thumbstrSmall == "":
                if mapgenUtils.isGeneratedMap(self.folderName):
                    self.setItemIcon("games/generated_map.png")
                else:
                    self.setItemIcon("games/unknown_map.png")
            else:
                self.parent.client.map_downloader.download_preview(
                    self.folderName, self._map_dl_request, self.thumbstrSmall,
                )

        # Ensure that the icon is set
        self.ensureIcon()

        self.updateVisibility()

    def setItemIcon(self, filename, themed=True):
        icon = util.THEME.icon(filename)
        if not themed:
            pixmap = QtGui.QPixmap(filename)
            if not pixmap.isNull():
                icon.addPixmap(
                    pixmap.scaled(
                        QtCore.QSize(self.ICONSIZE, self.ICONSIZE),
                    ),
                )
        self.setIcon(icon)

    def ensureIcon(self):
        if self.icon() is None or self.icon().isNull():
            self.setItemIcon("games/unknown_map.png")

    def _on_map_downloaded(self, mapname, result):
        filename, themed = result
        self.setItemIcon(filename, themed)
        self.ensureIcon()

    def shouldBeVisible(self):
        p = self.parent
        if p.searchString != "":
            if not (
                self.name.lower().find(p.searchString) != -1
                or (
                    self.description.lower().find(" " + p.searchString + " ")
                    != -1
                )
            ):
                return False
        if p.showType == "all":
            return True
        elif p.showType == "unranked":
            return self.unranked
        elif p.showType == "ranked":
            return not self.unranked
        elif p.showType == "installed":
            return maps.isMapAvailable(self.folderName)
        else:  # shouldn't happen
            return True

    def updateVisibility(self):
        self.setHidden(not self.shouldBeVisible())
        if len(self.description) < 200:
            descr = self.description
        else:
            descr = self.description[:197] + "..."

        maptype = ""
        if self.unranked:
            maptype = "Unranked map"
        if maps.isMapAvailable(self.folderName):
            color = "green"
        else:
            color = "white"

        self.setText(
            self.FORMATTER_MAP.format(
                color=color,
                version=str(self.version),
                title=self.name,
                description=descr,
                height=str(self.height),
                width=str(self.width),
                rating=str(self.rating),
                reviews=str(self.reviews),
                date=str(self.date),
                modtype=maptype,
            ),
        )

        self.setToolTip('<p width="230">{}</p>'.format(self.description))

    def __ge__(self, other):
        return not self.__lt__(self, other)

    def __lt__(self, other):
        if self.parent.sortType == "alphabetical":
            return self.name.lower() > other.name.lower()
        elif self.parent.sortType == "rating":
            if self.rating == other.rating:
                if self.reviews == other.reviews:
                    return self.name.lower() > other.name.lower()
                return self.reviews < other.reviews
            return self.rating < other.rating
        elif self.parent.sortType == "size":
            if self.height * self.width == other.height * other.width:
                return self.name.lower() > other.name.lower()
            return self.height * self.width < other.height * other.width
        elif self.parent.sortType == "date":
            # guard
            if self.date is None:
                return other.date is not None
            if self.date == other.date:
                return self.name.lower() > other.name.lower()
            return self.date < other.date
