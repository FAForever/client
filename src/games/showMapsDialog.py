import requests

from PyQt4 import QtCore, QtGui
from fa import maps
import util

import logging
logger = logging.getLogger(__name__)

FormClass, BaseClass = util.loadUiType("games/showMaps.ui")
# TODO import this from somewhere
FAF_API_URL = "https://api.faforever.com"


class ShowMapsDialog(FormClass, BaseClass):
    ladderMapPath = '/maps/ladder1v1'

    def __init__(self, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)
        self.setupUi(self)

        # TODO indicator if busy + label "waiting for server" "loading data" "processing data"

        # Used to draw the elements of the list in a custom way
        self.mapList.setItemDelegate(MapItemDelegate(self))

        self.loadMaps()

        # show dialog and block main window until it is closed
        self.exec_()

    def loadMaps(self):
        """
        Loads the Ladder maps using the api and generates the according MapItems which are then added to the list to
        be displayed.
        """
        # TODO use faf.api.apiclient
        r = requests.get(FAF_API_URL + '/maps/ladder1v1')
        logger.info(r.status_code)
        logger.info(r.headers)
        logger.info(r.json())

        if not r.status_code == 200:
            return

        data = r.json()['data']

        for item in data:
            map = MapItem(item['attributes'])
            self.mapList.addItem(map)


class MapItem(QtGui.QListWidgetItem):
    FORMATTER = unicode(util.readfile("games/formatters/map.qthtml"))

    TEXTWIDTH = 170
    ICONSIZE = 120
    PADDING = 10

    def __init__(self, mapdict, *args, **kwargs):
        QtGui.QListWidgetItem.__init__(self, *args, **kwargs)

        logger.info("Updating map")
        logger.info("{}".format(mapdict))
        self.description = mapdict.get('description', '')
        self.display_name = mapdict.get('display_name', '')
        self.technical_name = mapdict.get('technical_name', '')
        self.downloads = mapdict.get('downloads', 0)
        self.id = mapdict.get('id', -1)
        self.max_players = mapdict.get('max_players', 12)
        self.version = mapdict.get('version', -1)
        self.height = mapdict.get('height', 0)
        self.width = mapdict.get('width', 0)

        # Format the displayed map

        # Set the Icon for this map
        icon = maps.preview(self.technical_name)
        if not icon:
            icon = util.icon("games/unknown_map.png")
        self.setIcon(icon)

        self.setText(self.FORMATTER.format(mapname=self.display_name, version=self.version,
                                           maxplayers=self.max_players, size=self.size()))

        self.setToolTip(self.description)

    def size(self):
        """
        Translate the size in faf units to km.
        :return: The size of the map in km.
        """
        return int(max(self.width, self.height) * 10 / 512)


class MapItemDelegate(QtGui.QStyledItemDelegate):
    """
    Used to customize how a map is displayed. We get a big icon and some html text to describe it
    """

    def __init__(self, *args, **kwargs):
        QtGui.QStyledItemDelegate.__init__(self, *args, **kwargs)

    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)

        painter.save()

        html = QtGui.QTextDocument()
        html.setHtml(option.text)

        icon = QtGui.QIcon(option.icon)
        iconsize = icon.actualSize(option.rect.size())

        # clear icon and text before letting the control draw itself because we're rendering these parts ourselves
        option.icon = QtGui.QIcon()
        option.text = ""
        option.widget.style().drawControl(QtGui.QStyle.CE_ItemViewItem, option, painter, option.widget)

        # Icon
        icon.paint(painter, option.rect.adjusted(5-2, 5-2, 0, 0), QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Frame around the icon
        pen = QtGui.QPen()
        pen.setWidth(1)
        pen.setBrush(QtGui.QColor("#303030"))  # FIXME: This needs to come from theme.
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawRect(option.rect.left()+2, option.rect.top() + MapItem.PADDING, iconsize.width(), iconsize.height())

        # Description
        painter.translate(option.rect.left() + iconsize.width() + 10, option.rect.top()+10)
        clip = QtCore.QRectF(0, 0, option.rect.width()-iconsize.width() - 10 - 5, option.rect.height())
        html.drawContents(painter, clip)

        painter.restore()

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)

        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        html.setTextWidth(MapItem.TEXTWIDTH)
        return QtCore.QSize(MapItem.ICONSIZE + MapItem.TEXTWIDTH + MapItem.PADDING, MapItem.ICONSIZE)
