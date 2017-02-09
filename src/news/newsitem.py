import webbrowser

import util

from PyQt4 import QtCore
from PyQt4.QtCore import Qt, QObject, QEvent

import logging
logger = logging.getLogger(__name__)


FormClass, BaseClass = util.loadUiType("news/newsframe.ui")

class MouseFilter(QObject):
    clicked = QtCore.pyqtSignal()

    def __init__(self):
        QObject.__init__(self)
        self.doFilter = True

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.MouseButtonRelease:
            logger.info('eventFilter MouseButtonRelease')
            self.clicked.emit()
            return self.doFilter
        else:
            return False


class NewsFrame(FormClass, BaseClass):
    enterStyle = "background-color: #ffffff;"
    leaveStyle = "background-color: #aaaaaa;"
    clicked = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)
        self.setupUi(self)

        self.mf = MouseFilter()
        self.mf.clicked.connect(self.clicked)

        #self.setMouseTracking(True)
        self.setStyleSheet(self.leaveStyle)

        self.newsWebView.installEventFilter(self.mf)
        self.titleLabel.installEventFilter(self.mf)

        page = self.newsWebView.page()
        #page.mainFrame().setScrollBarPolicy(Qt.Vertical, Qt.ScrollBarAlwaysOff)
        page.setLinkDelegationPolicy(page.DelegateAllLinks)
        page.linkClicked.connect(self.linkClicked)

    def mouseReleaseEvent(self, ev):
        logger.info('clicked')
        self.clicked.emit()

    def linkClicked(self, url):
        webbrowser.open(url.toString())

    def enterEvent(self, ev):
        logger.info('enter')
        self.setStyleSheet(self.enterStyle)

    def leaveEvent(self, ev):
        logger.info('leave')
        self.setStyleSheet(self.leaveStyle)

    def set_content(self, title, content):
        self.content = (title, content)
        self.titleLabel.setText(title)
        self.newsWebView.setHtml(content)

    def collapse(self):
        self.newsWebView.hide()

    def expand(self):
        self.newsWebView.show()
        self.newsWebView.setHtml(self.content[1])

    def toggle(self):
        if self.newsWebView.isHidden():
            self.expand()
        else:
            self.collapse()
