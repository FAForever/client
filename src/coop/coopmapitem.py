from PyQt5 import QtCore, QtGui, QtWidgets

import util


class CoopMapItemDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, *args, **kwargs):
        QtWidgets.QStyledItemDelegate.__init__(self, *args, **kwargs)

    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)

        painter.save()

        html = QtGui.QTextDocument()
        textOption = QtGui.QTextOption()
        textOption.setWrapMode(QtGui.QTextOption.WordWrap)
        html.setDefaultTextOption(textOption)

        html.setTextWidth(option.rect.width())
        html.setHtml(option.text)

        # clear text before letting the control draw itself because we're
        # rendering these parts ourselves
        option.text = ""
        option.widget.style().drawControl(
            QtWidgets.QStyle.CE_ItemViewItem, option, painter, option.widget,
        )
        # Description
        painter.translate(option.rect.left(), option.rect.top())
        clip = QtCore.QRectF(0, 0, option.rect.width(), option.rect.height())
        html.drawContents(painter, clip)

        painter.restore()

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
        html = QtGui.QTextDocument()
        textOption = QtGui.QTextOption()
        textOption.setWrapMode(QtGui.QTextOption.WordWrap)
        html.setTextWidth(option.rect.width())
        html.setDefaultTextOption(textOption)
        html.setHtml(option.text)

        return QtCore.QSize(
            int(html.size().width()) + 10,
            int(html.size().height()) + 10,
        )


class CoopMapItem(QtWidgets.QTreeWidgetItem):

    FORMATTER_COOP = str(util.THEME.readfile("coop/formatters/coop.qthtml"))

    def __init__(self, uid, parent, *args, **kwargs):
        QtWidgets.QTreeWidgetItem.__init__(self, *args, **kwargs)

        self.uid = uid
        self.parent = parent

        self.name = None
        self.description = None
        self.mapUrl = None
        self.options = []

        self.setHidden(True)

    def update(self, message):
        """
        Updates this item from the message dictionary supplied
        """

        self.name = message["name"]
        self.mapUrl = message["filename"]
        self.description = message["description"]
        self.mod = message["featured_mod"]

        self.viewtext = self.FORMATTER_COOP.format(
            name=self.name,
            description=self.description,
        )

    def display(self, column):
        if column == 0:
            return self.viewtext
        if column == 1:
            return self.viewtext

    def data(self, column, role):
        if role == QtCore.Qt.DisplayRole:
            return self.display(column)
        elif role == QtCore.Qt.UserRole:
            return self
        return super(CoopMapItem, self).data(column, role)

    def __ge__(self, other):
        """ Comparison operator used for item list sorting """
        return not self.__lt__(other)

    def __lt__(self, other):
        """ Comparison operator used for item list sorting """
        # Default: uid
        return self.uid > other.uid
