from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from PyQt6 import QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QVBoxLayout

from src import util
from src.api.models.Map import Map
from src.api.models.Mod import Mod
from src.config import Settings
from src.qt.utils import block_signals
from src.qt.utils import center_widget_on_screen
from src.ui.busy_widget import BusyWidget
from src.vaults.detailswidget import DetailsWidget
from src.vaults.listitem import VaultListItem
from src.vaults.listwidget import VaultListWidget

if TYPE_CHECKING:
    from src.client._clientwindow import ClientWindow


class BrowseType(Enum):
    ALL = "All"
    RECOMMENDED = "Recommended"
    MOST_PLAYED = "Most Played"
    MOST_LIKED = "Most Liked"
    NEWEST = "Newest"


FormClass, BaseClass = util.THEME.loadUiType("vaults/vault.ui")


class Vault(FormClass, BaseClass, BusyWidget):
    def __init__(self, client: ClientWindow) -> None:
        BaseClass.__init__(self)
        self.setupUi(self)
        self.client = client

        self.searchButton.clicked.connect(self.search)
        self.searchInput.returnPressed.connect(self.search)

        self.itemList.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.itemList.currentItemChanged.connect(self.on_item_selected)
        self.itemList.setSpacing(10)

        placeholder = QLabel("<h1>Select an item to view details</h1>")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detailStack.addWidget(placeholder)

        self.SortTypeList.clear()
        self.SortTypeList.setCurrentIndex(0)
        self.SortTypeList.currentIndexChanged.connect(self.sort_changed)
        self.ShowTypeList.clear()
        self.ShowTypeList.currentIndexChanged.connect(self.show_changed)

        self.searchString = ""
        self.searchQuery = {}
        self.apiConnector = None

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
        self.lastButton.clicked.connect(lambda: self.goToPage(self.totalPages))
        self.resetButton.clicked.connect(self.reset_search)

        self.browseComboBox.addItems([browse.value for browse in BrowseType])
        self.browseComboBox.currentIndexChanged.connect(self.on_browse_type_changed)

        self.flowComboBox.addItems([flow.name for flow in self.itemList.Flow])
        self.flowComboBox.currentIndexChanged.connect(self.on_flow_type_changed)

        self._items: dict[str, VaultListItem] = {}

        self.UIButton.hide()
        self.uploadButton.hide()

        self.vault_type = type(self).__name__

        with Settings.group("vaults"):
            splitter_sizes = Settings.get(f"{self.vault_type}/splitter", type=list, default=[])
            if len(splitter_sizes) == 2:
                self.splitter.setSizes(list(map(int, splitter_sizes)))
            flow_type = Settings.get(
                f"{self.vault_type}/flow",
                type=self.itemList.Flow,
                default=self.itemList.Flow.LeftToRight,
            )
            self.itemList.setFlow(flow_type)
            self.itemList.setWrapping(flow_type == self.itemList.Flow.LeftToRight)
        self.splitter.splitterMoved.connect(self.save_splitter_sizes)

    def save_splitter_sizes(self) -> None:
        with Settings.group("vaults"):
            Settings.set(f"{self.vault_type}/splitter", self.splitter.sizes())

    def save_flow_type(self) -> None:
        with Settings.group("vaults"):
            Settings.set(f"{self.vault_type}/flow", self.itemList.flow())

    def on_flow_type_changed(self, index: int) -> None:
        flow_type = list(self.itemList.Flow)[index]
        self.itemList.setFlow(flow_type)
        self.itemList.setWrapping(flow_type == self.itemList.Flow.LeftToRight)
        self.save_flow_type()

    def on_browse_type_changed(self, index: int) -> None:
        browse_type = list(BrowseType)[index]
        match browse_type:
            case BrowseType.ALL:
                self.searchQuery = {}
            case BrowseType.RECOMMENDED:
                self.searchQuery = {"filter": "recommended=='true'"}
            case BrowseType.MOST_PLAYED:
                self.searchQuery = {"sort": "-gamesPlayed"}
            case BrowseType.MOST_LIKED:
                self.searchQuery = {"sort": "-reviewsSummary.lowerBound"}
            case BrowseType.NEWEST:
                self.searchQuery = {"sort": "-createTime"}

        with block_signals(self.SortTypeList):
            self.SortTypeList.setCurrentIndex(0)

        with block_signals(self.ShowTypeList):
            self.ShowTypeList.setCurrentIndex(0)

        self.goToPage(1)

    def showEvent(self, event: QShowEvent) -> None:
        self.busy_entered()
        BaseClass.showEvent(self, event)

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
    def goToPage(self, page: int) -> None:
        if self.apiConnector is None:
            return

        self._items.clear()
        self.itemList.clear()
        self.pageBox.setValue(page)
        self.pageNumber = self.pageBox.value()
        self.updateQuery(self.pageNumber)
        self.apiConnector.request_data(self.searchQuery)
        self.update_visibilities()

    def on_item_double_clicked(self, item: VaultListItem) -> None:
        dialog = QDialog(self)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        widget = self.create_details_widget(item.item_data)
        widget.item_availability_changed.connect(self.on_item_availability_changed)
        widget.ask_review()
        layout.addWidget(widget)
        dialog.setLayout(layout)
        dialog.setWindowTitle(f"Details - {item.item_data.display_name}")
        dialog.resize(800, 600)
        with Settings.group("vaults") as settings:
            dialog.restoreGeometry(settings.value("item_widget_geometry", dialog.saveGeometry()))
            center_widget_on_screen(dialog)
        dialog.exec()
        with Settings.group("vaults") as settings:
            settings.setValue("item_widget_geometry", dialog.saveGeometry())
        widget.disconnect()
        dialog.deleteLater()

    def on_item_selected(self, current: VaultListItem, previous: VaultListItem) -> None:
        if not current or self.splitter.sizes()[1] == 0:
            return
        details_widget = self.create_details_widget(current.item_data)
        details_widget.item_availability_changed.connect(self.on_item_availability_changed)
        details_widget.ask_review()
        self.show_details_widget(details_widget)

    def show_details_widget(self, widget: DetailsWidget) -> None:
        while self.detailStack.count() > 1:
            w = self.detailStack.widget(1)
            self.detailStack.removeWidget(w)
            w.disconnect()
            w.deleteLater()

        self.detailStack.addWidget(widget)
        self.detailStack.setCurrentIndex(1)

    def create_item(self, data: Map | Mod) -> VaultListWidget:
        return VaultListWidget(data, util.CACHE_DIR)

    def create_list_item(self, data: Map | Mod) -> VaultListItem:
        return VaultListItem(self.itemList, data)

    def create_details_widget(self, data: Map | Mod) -> DetailsWidget:
        assert self.client.me.player is not None
        return DetailsWidget(data, util.CACHE_DIR, self.client.me.player)

    @QtCore.pyqtSlot(dict)
    def items_info(self, message: dict) -> None:
        for value in message["values"]:
            item_key = value.xd
            if item_key in self._items:
                list_item = self._items[item_key]
            else:
                item = self.create_item(value)
                list_item = self.create_list_item(value)
                list_item.set_display_type(self.ShowTypeList.currentIndex())
                list_item.setSizeHint(item.sizeHint())
                self._items[item_key] = list_item
                self.itemList.setItemWidget(list_item, item)
            self.itemList.addItem(list_item)
        self.sort_items()
        self.update_visibilities()
        self.processMeta(message["meta"])

    def processMeta(self, message: dict) -> None:
        self.totalPages = message['page']['totalPages']
        self.totalRecords = message['page']['totalRecords']
        if self.totalPages < 1:
            self.totalPages = 1
        self.labelTotalPages.setText(str(self.totalPages))

    @QtCore.pyqtSlot(bool)
    def reset_search(self) -> None:
        self.searchString = ''
        self.searchInput.clear()
        self.searchQuery.clear()
        with block_signals(self.browseComboBox):
            self.browseComboBox.setCurrentIndex(0)
        self.goToPage(1)

    def search(self) -> None:
        self.searchString = self.searchInput.text().lower()
        if self.searchString == '' or self.searchString.replace(' ', '') == '':
            self.reset_search()
        else:
            self.searchString = self.searchString.strip()
            self.searchQuery = {"filter": f"displayName=='*{self.searchString}*'"}
            with block_signals(self.browseComboBox):
                self.browseComboBox.setCurrentIndex(0)
            self.goToPage(1)

    @QtCore.pyqtSlot()
    def busy_entered(self):
        if not self._items:
            self.goToPage(self.pageNumber)

    def update_visibilities(self) -> None:
        for item in self._items.values():
            item.update_visibility()
        self.sort_items()

    def on_item_availability_changed(self) -> None:
        current_item = self.itemList.currentItem()
        self.itemList.itemWidget(current_item).update_visibility()

    @QtCore.pyqtSlot(int)
    def sort_changed(self, index: int) -> None:
        for item in self._items.values():
            item.on_sort_type_changed(index)
        self.update_visibilities()

    @QtCore.pyqtSlot(int)
    def show_changed(self, index: int) -> None:
        for item in self._items.values():
            item.on_display_type_changed(index)
        self.update_visibilities()

    def sort_items(self) -> None:
        if self.SortTypeList.currentIndex() == 0:
            return
        self.itemList.sortItems(QtCore.Qt.SortOrder.DescendingOrder)
