from PyQt5 import QtCore, QtGui, QtWidgets

import util
import client

import logging
logger = logging.getLogger(__name__)

class NewsItemDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, *args, **kwargs):
        QtWidgets.QStyledItemDelegate.__init__(self, *args, **kwargs)

        html = QtGui.QTextDocument()
        to = QtGui.QTextOption()
        to.setWrapMode(QtGui.QTextOption.WordWrap)
        html.setDefaultTextOption(to)
        html.setTextWidth(NewsItem.TEXTWIDTH)

        self.html = html

    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)

        painter.save()

        self.html.setHtml(option.text)

        icon = QtGui.QIcon(option.icon)

        # clear icon and text before letting the control draw itself because we're rendering these parts ourselves
        option.icon = QtGui.QIcon()
        option.text = ""  
        option.widget.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, painter, option.widget)

        # Shadow (100x100 shifted 8 right and 8 down)
#        painter.fillRect(option.rect.left()+8, option.rect.top()+8, 100, 100, QtGui.QColor("#202020"))

#        # Icon  (110x110 adjusted: shifts top,left 3 and bottom,right -7 -> makes/clips it to 100x100)
#        icon.paint(painter, option.rect.adjusted(3, 3, -7, -7), QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)

        # Frame around the icon (100x100 shifted 3 right and 3 down)
#        pen = QtWidgets.QPen()
#        pen.setWidth(1)
#        pen.setBrush(QtGui.QColor("#303030"))  # FIXME: This needs to come from theme.
#        pen.setCapStyle(QtCore.Qt.RoundCap)
#        painter.setPen(pen)
#        painter.drawRect(option.rect.left() + 3, option.rect.top() + 3, 100, 100)

        # Description (text right of map icon(100), shifted 10 more right and 10 down)
        painter.translate(option.rect.left() + 10, option.rect.top()+10)
        clip = QtCore.QRectF(0, 0, option.rect.width() - 10 - 5, option.rect.height())
        self.html.drawContents(painter, clip)

        painter.restore()

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)

        self.html.setHtml(option.text)

        return QtCore.QSize(NewsItem.TEXTWIDTH + NewsItem.PADDING, NewsItem.TEXTHEIGHT)


class NewsItem(QtWidgets.QListWidgetItem):
    TEXTWIDTH = 230
    TEXTHEIGHT = 85
    PADDING = 10

    FORMATTER = str(util.readfile("news/formatters/newsitem.qhtml"))

    def __init__(self, newsPost, *args, **kwargs):
        QtWidgets.QListWidgetItem.__init__(self, *args, **kwargs)

        self.newsPost = newsPost


        self.setText(self.FORMATTER.format(
            author=newsPost['author'][0]['name'],
            date=newsPost['date'],
            title=newsPost['title']
            ))

    def __ge__(self, other):
        """ Comparison operator used for item list sorting """
        return not self.__lt__(other)

    def __lt__(self, other):
        return self.newsPost['date'].__lt__(other.newsPost['date'])
