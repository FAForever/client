import logging

from PyQt5 import QtCore, QtGui, QtWidgets

import util
from downloadManager import DownloadRequest
from ui.busy_widget import BusyWidget

logger = logging.getLogger(__name__)


FormClass, BaseClass = util.THEME.loadUiType("vaults/vault.ui")


class Vault(FormClass, BaseClass, BusyWidget):
    def __init__(self, client, *args, **kwargs):
        QtCore.QObject.__init__(self, *args, **kwargs)
        self.setupUi(self)
        self.client = client

        self.itemList.setItemDelegate(VaultItemDelegate(self))

        self.searchButton.clicked.connect(self.search)
        self.searchInput.returnPressed.connect(self.search)

        self.SortTypeList.setCurrentIndex(0)
        self.SortTypeList.currentIndexChanged.connect(self.sortChanged)
        self.ShowTypeList.currentIndexChanged.connect(self.showChanged)

        self.client.lobby_info.vaultMeta.connect(self.metaInfo)

        self.sortType = "alphabetical"
        self.showType = "all"
        self.searchString = ""
        self.searchQuery = dict(include='latestVersion,reviewsSummary')
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
        self.resetButton.clicked.connect(self.resetSearch)

        self._items = {}
        self._installed_items = {}

        for type_ in ["Upload Date", "Rating"]:
            self.SortTypeList.addItem(type_)

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
        if self.apiConnector is not None:
            self._items.clear()
            self.itemList.clear()
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
        self.searchString = ''
        self.searchInput.clear()
        self.searchQuery = dict(include='latestVersion,reviewsSummary')
        self.goToPage(1)

    def search(self):
        self.searchString = self.searchInput.text().lower()
        if self.searchString == '' or self.searchString.replace(' ', '') == '':
            self.resetSearch()
        else:
            self.searchString = self.searchString.strip()
            self.searchQuery = dict(
                include='latestVersion,reviewsSummary',
                filter='displayName=="*{}*"'.format(self.searchString),
            )
            self.goToPage(1)

    @QtCore.pyqtSlot()
    def busy_entered(self):
        if not self._items:
            self.goToPage(self.pageNumber)

    def updateVisibilities(self):
        logger.debug(
            "Updating visibilities with sort '{}' and visibility '{}'"
            .format(self.sortType, self.showType),
        )
        for _item in self._items:
            self._items[_item].updateVisibility()
        self.itemList.sortItems(1)


class VaultItemDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, *args, **kwargs):
        QtWidgets.QStyledItemDelegate.__init__(self, *args, **kwargs)

    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)

        painter.save()

        html = QtGui.QTextDocument()
        html.setHtml(option.text)

        icon = QtGui.QIcon(option.icon)
        iconsize = QtCore.QSize(VaultItem.ICONSIZE, VaultItem.ICONSIZE)

        # clear icon and text before letting the control draw itself because
        # we're rendering these parts ourselves
        option.icon = QtGui.QIcon()
        option.text = ""
        option.widget.style().drawControl(
            QtWidgets.QStyle.CE_ItemViewItem, option, painter, option.widget,
        )

        # Shadow
        painter.fillRect(
            option.rect.left() + 7,
            option.rect.top() + 7,
            iconsize.width(),
            iconsize.height(),
            QtGui.QColor("#202020"),
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
        html.setTextWidth(VaultItem.TEXTWIDTH)
        return QtCore.QSize(
            (
                VaultItem.ICONSIZE
                + VaultItem.TEXTWIDTH
                + VaultItem.PADDING
            ),
            VaultItem.ICONSIZE + VaultItem.PADDING,
        )


class VaultItem(QtWidgets.QListWidgetItem):
    TEXTWIDTH = 230
    ICONSIZE = 100
    PADDING = 10

    def __init__(self, parent, *args, **kwargs):
        QtWidgets.QListWidgetItem.__init__(self, *args, **kwargs)
        self.parent = parent

        self.name = ""
        self.description = ""
        self.trimmedDescription = ""
        self.version = 0
        self.rating = 0
        self.reviews = 0
        self.date = None

        self.itemType_ = ""
        self.color = "white"

        self.link = ""
        self.setHidden(True)

        self._item_dl_request = DownloadRequest()
        self._item_dl_request.done.connect(self._on_item_downloaded)

    def update(self):
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

    def _on_item_downloaded(self, mapname, result):
        filename, themed = result
        self.setItemIcon(filename, themed)
        self.ensureIcon()

    def updateVisibility(self):
        self.setHidden(not self.shouldBeVisible())
        if len(self.description) < 200:
            self.trimmedDescription = self.description
        else:
            self.trimmedDescription = self.description[:197] + "..."

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
            if self.date is None:
                return other.date is not None
            if self.date == other.date:
                return self.name.lower() > other.name.lower()
            return self.date < other.date
