from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt

import util
import client
import re
from .newsitem import NewsItem, NewsItemDelegate
from .newsmanager import NewsManager

import base64

import logging

logger = logging.getLogger(__name__)

FormClass, BaseClass = util.loadUiType("news/news.ui")

class NewsWidget(FormClass, BaseClass):
    CSS = """
    div#container { width: 100%; }
    img { display: block; max-width: 100%; height: auto !important; }
    """

    def __init__(self, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)

        self.setupUi(self)

        client.instance.whatNewTab.layout().addWidget(self)

        self.newsManager = NewsManager(self)

        self.newsWebView.settings().setUserStyleSheetUrl(QtCore.QUrl(
                'data:text/css;charset=utf-8;base64,' + base64.b64encode(self.CSS)
            ))

        self.newsList.setIconSize(QtCore.QSize(0,0))
        self.newsList.setItemDelegate(NewsItemDelegate(self))
        self.newsList.itemClicked.connect(self.itemClicked)

    def addNews(self, newsPost):
        newsItem = NewsItem(newsPost, self.newsList)

    def itemClicked(self, item):
        self.newsWebView.setHtml(
            item.newsPost['body']
        )
