import logging
import webbrowser

from PyQt5 import QtCore, QtWidgets

import util
from config import Settings
from util.qt import ExternalLinkPage

from .newsitem import NewsItem, NewsItemDelegate
from .newsmanager import NewsManager

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

FormClass, BaseClass = util.THEME.loadUiType("news/news.ui")


class NewsWidget(FormClass, BaseClass):
    CSS = util.THEME.readstylesheet('news/news_webview.css')

    HTML = str(util.THEME.readfile('news/news_webview_frame.html'))

    def __init__(self, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)

        self.setupUi(self)

        self.newsManager = NewsManager(self)
        self.newsItems = []

        # open all links in external browser
        self.newsWebView.setPage(ExternalLinkPage(self))

        # hide webview until loaded to avoid FOUC
        self.hider = Hider()
        self.hider.hide(self.newsWebView)
        self.newsWebView.loadFinished.connect(self.loadFinished)

        self.settingsFrame.hide()
        self.hideNewsEdit.setText(Settings.get('news/hideWords', ""))

        self.newsList.setIconSize(QtCore.QSize(0, 0))
        self.newsList.setItemDelegate(NewsItemDelegate(self))
        self.newsList.currentItemChanged.connect(self.itemChanged)
        self.newsSettings.pressed.connect(self.showSettings)
        self.showAllButton.pressed.connect(self.showAll)
        self.hideNewsEdit.textEdited.connect(self.updateNewsFilter)
        self.hideNewsEdit.cursorPositionChanged.connect(self.showEditToolTip)

    def addNews(self, newsPost):
        newsItem = NewsItem(newsPost, self.newsList)
        self.newsItems.append(newsItem)

    # QtWebEngine has no user CSS support yet, so let's just prepend it to the HTML
    def _injectCSS(self, body, link, img):
        img = '<div style="float:left;"><p style="float:left;"><img src=' + img + ' border="1px" hspace=20></p>'
        body = body + '</div>'
        link = '<div style="clear:left;"><a href=' + link + ' style="margin: 0px 0px 0px 20px">Open in your Web browser</a></div>'
        return '<style type="text/css">{}</style>'.format(self.CSS) + img + body + link

    def updateNews(self):
        self.hider.hide(self.newsWebView)
        self.newsItems = []
        self.newsList.clear()
        self.newsManager.WpApi.download()

    def itemChanged(self, current, previous):
        if current is not None:
            if current.newsPost['external_link'] == '':
                link = current.newsPost['link']
            else:
                link = current.newsPost['external_link']
            self.newsWebView.page().setHtml(self.HTML.format(title=current.newsPost['title'],
                                                             content=self._injectCSS(current.newsPost['excerpt'],
                                                                                     link,
                                                                                     current.newsPost['img_url']
                                                             )
                                            )
            )

    def linkClicked(self, url):
        webbrowser.open(url.toString())

    def loadFinished(self, ok):
        self.hider.unhide(self.newsWebView)
        self.newsWebView.loadFinished.disconnect(self.loadFinished)

    def showAll(self):
        for item in self.newsItems:
            item.setHidden(False)
        self.updateLabel(0)

    def showEditToolTip(self):
        """Default tooltips are too slow and disappear when user starts typing"""
        widget = self.hideNewsEdit
        position = widget.mapToGlobal(QtCore.QPoint(0 + widget.width(), 0 - widget.height() / 2))
        QtWidgets.QToolTip.showText(position, "To separate multiple words use commas: nomads,server,dev")

    def showSettings(self):
        if self.settingsFrame.isHidden():
            self.settingsFrame.show()
        else:
            self.settingsFrame.hide()

    def updateNewsFilter(self, text=False):
        if text is not False:
            Settings.set('news/hideWords', text)

        filterList = Settings.get('news/hideWords', "").lower().split(",")
        newsHidden = 0

        if filterList[0]:
            for item in self.newsItems:
                for word in filterList:
                    if word in item.text().lower():
                        item.setHidden(True)
                        newsHidden += 1
                        break
                    else:
                        item.setHidden(False)
        else:
            for item in self.newsItems:
                item.setHidden(False)

        self.updateLabel(newsHidden)

    def updateLabel(self, number):
        self.totalHidden.setText("NEWS HIDDEN: " + str(number))
