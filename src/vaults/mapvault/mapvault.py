from __future__ import annotations

import logging
import os
from stat import S_IWRITE
from typing import TYPE_CHECKING

from PyQt6 import QtCore
from PyQt6 import QtWidgets

from src.api.models.Map import Map
from src.api.vaults_api import MapApiConnector
from src.api.vaults_api import MapPoolApiConnector
from src.fa import maps
from src.fa.maps_.map_utils import get_save_file
from src.vaults import luaparser
from src.vaults.mapvault.mapdetails import MapDetailsWidget
from src.vaults.mapvault.maplistitem import MapDisplayType
from src.vaults.mapvault.maplistitem import MapListItem
from src.vaults.mapvault.maplistitem import MapSortType
from src.vaults.mapvault.maplistwidget import MapListWidget
from src.vaults.vault import Vault

if TYPE_CHECKING:
    from src.client._clientwindow import ClientWindow

logger = logging.getLogger(__name__)


class MapVault(Vault[Map]):
    def __init__(self, client: ClientWindow) -> None:
        logger.debug("Map Vault tab instantiating")
        super().__init__(client)
        self.installed_maps = maps.getUserMaps()

        for sort_type in MapSortType:
            self.SortTypeList.addItem(sort_type.value)
        for display_type in MapDisplayType:
            self.ShowTypeList.addItem(display_type.value)

        self.mapApiConnector = MapApiConnector()
        self.mapPoolApiConnector = MapPoolApiConnector()
        self.mapApiConnector.data_ready.connect(self.items_info)
        self.mapPoolApiConnector.data_ready.connect(self.items_info)

        self.apiConnector = self.mapApiConnector

    def create_item_widget(self, data: Map) -> MapListWidget:
        return MapListWidget(data)

    def create_list_item(self, data: Map) -> MapListItem:
        return MapListItem(self.itemList, data)

    def create_details_widget(self, data: Map) -> MapDetailsWidget:
        assert self.client.me.player is not None
        return MapDetailsWidget(data, self.client.me.player)

    def requestMapPool(self, queue_name: str, rating: int) -> None:
        self.apiConnector = self.mapPoolApiConnector
        self.searchQuery = {
            "filter": ";".join((
                f"mapPool.matchmakerQueueMapPool.matchmakerQueue.technicalName=={queue_name}",
                (
                    f"(mapPool.matchmakerQueueMapPool.minRating=le={rating!r},"
                    "mapPool.matchmakerQueueMapPool.minRating=isnull='true')"
                ),
                (
                    f"(mapPool.matchmakerQueueMapPool.maxRating=gt={rating!r},"
                    "mapPool.matchmakerQueueMapPool.maxRating=isnull='true')"
                ),
            )),
        }
        self.goToPage(1)
        self.apiConnector = self.mapApiConnector

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
                        "There were %s errors and %s warnings",
                        scenariolua.errors,
                        scenariolua.warnings,
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
                            QtWidgets.QMessageBox.StandardButton.Yes,
                            QtWidgets.QMessageBox.StandardButton.No,
                        )
                    else:
                        uploadmap = QtWidgets.QMessageBox.StandardButton.Yes
                    if uploadmap == QtWidgets.QMessageBox.StandardButton.Yes:
                        savelua = luaparser.luaParser(get_save_file(mapDir) or "")
                        saveInfos = savelua.parse({
                            'markers>mass*>position': 'mass:__parent__',
                            'markers>hydro*>position': 'hydro:__parent__',
                            'markers>army*>position': 'army:__parent__',
                        })
                        if savelua.error or savelua.warning:
                            logger.debug(
                                "There were %s errors and %s warnings",
                                scenariolua.errors,
                                scenariolua.warnings,
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
