from PyQt5 import QtCore, QtWidgets, QtGui
import util
import os
import time
import datetime

from util.gameurl import GameUrl, GameUrlType
from config import Settings
from util import MAP_PREVIEW_LARGE_DIR
from downloadManager import DownloadRequest

import logging
logger = logging.getLogger(__name__)

filtersSettings = {
    "Player name": dict(
        filterString = "playerStats.player.login", 
        operators = ["contains", "is", "is not"]),
    "One of global ratings": dict(
        filterString = "playerStats.player.globalRating.rating", 
        operators = [">", "<"]),
    "One of ladder ratings": dict(
        filterString = "playerStats.player.ladder1v1Rating.rating", 
        operators = [">", "<"]),
    "Game mod name": dict(
        filterString = "featuredMod.technicalName", 
        operators = ["contains", "is", "is not"]),
    "Map name": dict(
        filterString = "mapVersion.map.displayName", 
        operators = ["contains", "is", "is not"]),
    "Player faction": dict(
        filterString = "playerStats.faction", 
        operators = ["is", "is not"],
        values = ["AEON", "CYBRAN", "UEF", "SERAPHIM", "NOMAD", "CIVILIAN"]),
    "Player start position": dict(
        filterString = "playerStats.startSpot", 
        operators = ["is", "is not"]),
    "Max players (map)": dict(
        filterString = "mapVersion.maxPlayers", 
        operators = ["is", "is not", ">", "<"]),
    "Replay ID": dict(
        filterString = "id", 
        operators = ["is"]),
    "Title": dict(
        filterString = "name", 
        operators = ["contains", "is", "is not"]),
    "Start time": dict(
        filterString = "startTime", 
        operators = [">", "<"]),
    "Validity": dict(
        filterString = "validity", 
        operators = ["is"],
        values = ["VALID", "TOO_MANY_DESYNCS", "WRONG_VICTORY_CONDITION", "NO_FOG_OF_WAR", "CHEATS_ENABLED",
                  "PREBUILT_ENABLED", "NORUSH_ENABLED", "BAD_UNIT_RESTRICTIONS", "BAD_MAP", "TOO_SHORT"]),
    "Victory condition": dict(
        filterString = "victoryCondition", 
        operators = ["is", "is not"],
        values = ["DEMORALIZATION", "DOMINATION", "ERADICATION", "SANDBOX", "UNKNOWN"])
}

operators = {
    'is': '=="{}"',
    'is not': '!="{}"',
    'contains': '=="*{}*"',
    '>': '=gt="{}"',
    '<': '=lt="{}"',
}


class ReplayToolboxHandler(object):
    activePage = Settings.get('replay/activeTboxPage', "Hide all", str)

    def __init__(self, wigetHandler, widget, dispatcher, client, gameset, playerset):
        self._w = widget
        self._dispatcher = dispatcher
        self.client = client
        self._gameset = gameset
        self._playerset = playerset
        self.widgetHandler = wigetHandler
        
        self._map_dl_request = DownloadRequest()
        self._map_dl_request.done.connect(self._on_map_preview_downloaded)
        
        w = self._w
        
        self.hidden = False
        self.pageChanged = False
        self.mapPreview = False
        self.numOfFiltersLines = 6
        self.filtersList = []
        self.numOfPages = w.replayToolBox.count()
        self.hideAllIndex = self.numOfPages - 1
        self.tboxMinHeight = w.replayToolBox.minimumHeight()
        self.widgetMinHeight = w.widget_3.minimumHeight()

        w.replayToolBox.currentChanged.connect(self.tboxChanged)
        w.advSearchButton.pressed.connect(self.advancedSearch)
        w.advResetButton.pressed.connect(self.resetAll)
        w.mapPreviewLabel.currentMap = None

        self.setupTboxPages()
        self.setupComboBoxes()

    def setupTboxPages(self):
        ''' 
        A hack to imitate 'collapse all' function 
        + some style tweaks that can't be done via css or QtDesigner.
        Ideally, we should rewrite QToolBox and make our own :)
        '''
        w = self._w
        children = w.replayToolBox.children()

        for widget in children:
            if isinstance(widget, QtWidgets.QAbstractButton):
                widget.clicked.connect(self.tboxTitleClicked)
                widget.setStyleSheet("font-size:9pt")

        # make our empty page invisible
        children[-1].setStyleSheet("background-color: transparent; border-width: 0px")
        children[-2].setStyleSheet("max-height: 0px")

        for n in range (0, self.numOfPages):
            if w.replayToolBox.itemText(n) == self.activePage:
                w.replayToolBox.setCurrentIndex(n)
                break
                
        if self.activePage == "Hide all":
            self.adjustTboxSize(hide = True)
        elif self.activePage == "Map Preview":
            self.mapPreview = True
            
    def adjustTboxSize(self, hide = None):
        ''' a part of "collapse all" hack'''
        if hide:
            self.hidden = True
            height = 35 * self.numOfPages
            self._w.widget_3.setMaximumHeight(height)
            self._w.widget_3.setMinimumHeight(0)
            
            self._w.replayToolBox.setMaximumHeight(height)
            self._w.replayToolBox.setMinimumHeight(0)
        else:
            self.hidden = False
            self._w.widget_3.setMaximumHeight(1000)
            self._w.widget_3.setMinimumHeight(self.widgetMinHeight)
            
            self._w.replayToolBox.setMaximumHeight(1000)
            self._w.replayToolBox.setMinimumHeight(self.tboxMinHeight)
            
    def tboxChanged(self, index):
        page = self._w.replayToolBox.itemText(index)
        if page == "Map Preview":
            self.mapPreview = True
        else:
            self.mapPreview = False

        Settings.set('replay/activeTboxPage', page)
        self.pageChanged = True
    
    def tboxTitleClicked(self, arg):
        if not self.pageChanged:
            self.adjustTboxSize(hide = True)
            self._w.replayToolBox.setCurrentIndex(self.hideAllIndex)
        elif self.hidden:
            self.adjustTboxSize(hide = False)

        self.pageChanged = False


    ####    Advanced search section   ####
    ######################################

    def setupComboBoxes(self):
        for n in range (1, self.numOfFiltersLines + 1):
            filterComboBox = getattr(self._w, "filter{}".format(n))
            filterComboBox.operatorBox = getattr(self._w, "operator{}".format(n))
            filterComboBox.valueBox = getattr(self._w, "value{}".format(n))
            filterComboBox.layout = getattr(self._w, "filterHorizontal{}".format(n))
            filterComboBox.dateEdit = None
            filterComboBox.dateIsActive = False
            
            filterComboBox.currentIndexChanged.connect(self.filterChanged)
            filterComboBox.addItem("")

            for key, v in filtersSettings.items():
                filterComboBox.addItem(key)
            self.filtersList.append(filterComboBox)

        self._w.filter1.setCurrentIndex(1)
    
    def filterChanged(self):
        '''Setup operator and value comboBoxes according to selected filter'''
        filterWidget = self._w.sender()
        filterName = filterWidget.currentText()
        operatorBox = filterWidget.operatorBox
        valueBox = filterWidget.valueBox

        operatorBox.clear()
        valueBox.clear()

        if filterName:
            if filterName == "Start time": #show date edit and hide valueBox
                filterWidget.valueBox.hide()
                if not filterWidget.dateEdit:
                    self.createDateEdit(filterWidget, valueBox)
                else:
                    filterWidget.dateEdit.show()
                filterWidget.dateIsActive = True
            elif filterWidget.dateIsActive:
                filterWidget.dateEdit.hide()
                filterWidget.valueBox.show()
                filterWidget.dateIsActive = False

            for operator in filtersSettings[filterName]['operators']:
                operatorBox.addItem(operator)

            if 'values' in filtersSettings[filterName]:
                for val in filtersSettings[filterName]['values']:
                    valueBox.addItem(val)
        elif filterWidget.dateIsActive:
            # Switch from "Start time" filter to empty
            filterWidget.dateEdit.hide()
            filterWidget.dateIsActive = False
            filterWidget.valueBox.show()

    def createDateEdit(self, filterWidget, valueBox):
        filterWidget.dateEdit = QtWidgets.QDateEdit(QtCore.QDate.currentDate(), valueBox)
        filterWidget.dateEdit.setCalendarPopup(True)
        filterWidget.layout.addWidget(filterWidget.dateEdit)

    def advancedSearch(self):
        parameters = self.widgetHandler.defaultSearchParams.copy()
        
        filters = self.prepareFilters()

        if filters:
            parameters["filter"] = filters

        self.widgetHandler.apiConnector.requestData(parameters)
        
    def prepareFilters(self):
        finalFilters = []

        for filterBox in self.filtersList:
            filterName = filterBox.currentText()
            opName = filterBox.operatorBox.currentText()
            value = filterBox.valueBox.currentText()

            if filterName:
                filterString = filtersSettings[filterName]["filterString"]

                if filterName == "Start time":
                    startDate = filterBox.dateEdit.date().toString('yyyy-MM-dd')
                    if opName == ">":
                        finalFilters.append(filterString + operators[opName].format(startDate+"T00:00:00Z"))
                    else:
                        finalFilters.append(filterString + operators[opName].format(startDate+"T23:59:59Z"))
                elif value:
                    finalFilters.append(filterString + operators[opName].format(value))
                    
        if len(finalFilters) > 0:
            return "({})".format(";".join(finalFilters))

        return None
    
    def resetAll(self):
        for filterWidget in self.filtersList:
            filterWidget.setCurrentIndex(0)
            filterWidget.valueBox.setEditText("")

           
     ####    Map preview section   ####
     ##################################
     
    def updateMapPreview(self):
        selectedReplay = self.widgetHandler.selectedReplay
        if selectedReplay and hasattr(selectedReplay, "mapname"):
            preview = self._w.mapPreviewLabel
            if selectedReplay.mapname != "unknown" and selectedReplay.mapname != preview.currentMap:
                imgPath = os.path.join(MAP_PREVIEW_LARGE_DIR, selectedReplay.mapname + ".png")

                if os.path.isfile(imgPath):
                    pix = QtGui.QPixmap(imgPath)
                    preview.setPixmap(pix)
                    preview.currentMap = selectedReplay.mapname
                else:
                    self.client.map_downloader.download_preview(selectedReplay.mapname, self._map_dl_request, 
                                                                url = selectedReplay.previewUrlLarge, large = True)

    def _on_map_preview_downloaded(self, mapname, result):
        if mapname == self.widgetHandler.selectedReplay.mapname:
            self.updateMapPreview()