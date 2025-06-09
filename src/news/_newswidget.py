import logging
import os.path

from PyQt6 import QtWidgets
from PyQt6.QtCore import QPoint
from PyQt6.QtCore import QSize
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QImage
from PyQt6.QtGui import QTextDocument
from PyQt6.QtNetwork import QNetworkAccessManager

from src import util
from src.config import Settings
from src.downloadManager import Downloader
from src.downloadManager import DownloadRequest

from .newsitem import NewsItem
from .newsitem import NewsItemDelegate
from .newsmanager import NewsManager

logger = logging.getLogger(__name__)


FormClass, BaseClass = util.THEME.loadUiType("news/news.ui")


class NewsWidget(FormClass, BaseClass):
    CSS = util.THEME.readstylesheet('news/news_style.css')

    HTML = util.THEME.readfile('news/news_page.html')

    def __init__(self, *args, **kwargs) -> None:
        BaseClass.__init__(self, *args, **kwargs)

        self.setupUi(self)

        self.nam = QNetworkAccessManager()
        self._downloader = Downloader(util.NEWS_CACHE_DIR)
        self._images_dl_request = DownloadRequest()
        self._images_dl_request.done.connect(self.item_image_downloaded)

        self.newsManager = NewsManager(self)
        self.newsItems = []

        # open all links in external browser
        self.newsTextBrowser.setOpenExternalLinks(True)

        self.settingsFrame.hide()
        self.hideNewsEdit.setText(Settings.get('news/hideWords', ""))

        self.newsList.setIconSize(QSize(0, 0))
        self.newsList.setItemDelegate(NewsItemDelegate(self))
        self.newsList.currentItemChanged.connect(self.itemChanged)
        self.newsSettings.pressed.connect(self.showSettings)
        self.showAllButton.pressed.connect(self.showAll)
        self.hideNewsEdit.textEdited.connect(self.updateNewsFilter)
        self.hideNewsEdit.cursorPositionChanged.connect(self.showEditToolTip)

    def addNews(self, newsPost):
        newsItem = NewsItem(newsPost, self.newsList)
        self.newsItems.append(newsItem)

    def download_image(self, img_url: str) -> None:
        name = os.path.basename(img_url)
        self._downloader.download(name, self._images_dl_request, img_url)

    def add_image_resource(self, image_name: str, image_path: str) -> None:
        doc = self.newsTextBrowser.document()
        if doc.resource(QTextDocument.ResourceType.ImageResource, QUrl(image_name)):
            return
        img = QImage(image_path)
        scaled = img.scaled(QSize(600, 338))
        doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(image_name), scaled)

    def item_image_downloaded(self, image_name: str, result: tuple[str, bool]) -> None:
        image_path, download_failed = result
        if not download_failed:
            self.add_image_resource(image_name, image_path)
        self.show_newspage()

    def itemChanged(self, current: NewsItem | None, previous: NewsItem | None) -> None:
        if current is None:
            return

        url = current.newsPost["img_url"]
        image_name = os.path.basename(url)
        image_path = os.path.join(util.NEWS_CACHE_DIR, image_name)
        if os.path.isfile(image_path):
            self.add_image_resource(image_name, image_path)
            self.show_newspage()
        else:
            self._downloader.download(image_name, self._images_dl_request, url)

    def show_newspage(self) -> None:
        current = self.newsList.currentItem()

        if current.newsPost['external_link'] == '':
            external_link = current.newsPost['link']
        else:
            external_link = current.newsPost['external_link']

        image_name = os.path.basename(current.newsPost["img_url"])
        content = current.newsPost["excerpt"].strip().removeprefix("<p>").removesuffix("</p>")
        html = self.HTML.format(
            style=self.CSS,
            title=current.newsPost['title'],
            content=content,
            img_source=image_name,
            external_link=external_link,
        )
        self.newsTextBrowser.setHtml(html)

    def showAll(self):
        for item in self.newsItems:
            item.setHidden(False)
        self.updateLabel(0)

    def showEditToolTip(self) -> None:
        """
        Default tooltips are too slow and disappear when user starts typing
        """
        widget = self.hideNewsEdit
        position = widget.mapToGlobal(
            QPoint(0 + widget.width(), 0 - widget.height() / 2),
        )
        QtWidgets.QToolTip.showText(
            position,
            "To separate multiple words use commas: nomads,server,dev",
        )

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
