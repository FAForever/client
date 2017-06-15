from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

import webbrowser
import util
import client
import re
from .newsitem import NewsItem, NewsItemDelegate
from .newsmanager import NewsManager

from util.qt import ExternalLinkPage

import base64

import logging

logger = logging.getLogger(__name__)

class Hider(QtCore.QObject):
    """
    Hides a widget by blocking its paint event. This is useful if a
    widget is in a layout that you do not want to change when the
    widget is hidden.
    """
    def __init__(self, parent=None):
        super(Hider, self).__init__(parent)

    def eventFilter(self, obj, ev):
        return ev.type() == QtCore.QEvent.Paint

    def hide(self, widget):
        widget.installEventFilter(self)
        widget.update()

    def unhide(self, widget):
        widget.removeEventFilter(self)
        widget.update()

    def hideWidget(self, sender):
        if sender.isWidgetType():
            self.hide(sender)

FormClass, BaseClass = util.loadUiType("news/news.ui")

class NewsWidget(FormClass, BaseClass):
    CSS = util.readstylesheet('news/news_webview.css')

    HTML = str(util.readfile('news/news_webview_frame.html'))

    def __init__(self, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)

        self.setupUi(self)

        client.instance.whatNewTab.layout().addWidget(self)

        self.newsManager = NewsManager(self)

        # open all links in external browser
        self.newsWebView.setPage(ExternalLinkPage(self))

        # hide webview until loaded to avoid FOUC
        self.hider = Hider()
        self.hider.hide(self.newsWebView)
        self.newsWebView.loadFinished.connect(self.loadFinished)

        self.newsList.setIconSize(QtCore.QSize(0,0))
        self.newsList.setItemDelegate(NewsItemDelegate(self))
        self.newsList.currentItemChanged.connect(self.itemChanged)

    def addNews(self, newsPost):
        newsItem = NewsItem(newsPost, self.newsList)

    # QtWebEngine has no user CSS support yet, so let's just prepend it to the HTML
    def _injectCSS(self, body):
        return '<style type="text/css">{}</style>'.format(self.CSS) + body

    def itemChanged(self, current, previous):
        self.newsWebView.page().setHtml(self.HTML.format(
            title = current.newsPost['title'],
            content = self._injectCSS(current.newsPost['body']),
        ))

    def linkClicked(self, url):
        webbrowser.open(url.toString())

    def loadFinished(self, ok):
        self.hider.unhide(self.newsWebView)
        self.newsWebView.loadFinished.disconnect(self.loadFinished)

