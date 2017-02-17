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
    img { display: block; max-width: 100%; height: auto !important; }
    body {
        font-family: "Open Sans", "Helvetica Neue", Helvetica, Arial, sans-serif;
        font-size: 15px;
        line-height: 1.4;
        color: #222222;
        padding-top: 20px;
    }
    h1 {
        font-family: 'Yanone Kaffeesatz', sans-serif;
        font-size: 50px;
        text-align: center;
        margin-bottom: 20px;
        margin-top: 0px;
    }
    hr {
        display: block;
        margin-top: -10px;
        margin-bottom: 20px;
        margin-left: auto;
        margin-right: auto;
        border-style: solid;
        border-width: 3px;
    }
    """

    HTML = u"""
    <head>
    <link href="https://fonts.googleapis.com/css?family=Yanone+Kaffeesatz" rel="stylesheet" type="text/css">
    </head>
    <body>
    <h1>{title}</h1>
    <hr>
    <div id="container">
    {content}
    </div>
    </body>
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
        self.newsWebView.setHtml(self.HTML.format(
            title = item.newsPost['title'],
            content = item.newsPost['body'],
        ))
