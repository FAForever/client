import logging
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView

from src import util

logger = logging.getLogger(__name__)

# Safely load the default container UI
FormClass, BaseClass = util.THEME.loadUiType("news/news.ui")
class NewsWidget(FormClass, BaseClass):
    NEWS_FEED_URL = "https://faforever.github.io/FAF-Newsfeed/"

    def __init__(self, parent: QWidget | None = None) -> None:
        BaseClass.__init__(self, parent)
        self.setupUi(self)

        # Check if news.ui already defines a "newsLayout", otherwise build one
        if hasattr(self, 'newsLayout') and self.newsLayout is not None:
            layout = self.newsLayout
        else:
            layout = QVBoxLayout(self)
            self.setLayout(layout)

        # Inject the new WebEngine client
        self.browser = QWebEngineView(self)
        self.browser.setUrl(QUrl(self.NEWS_FEED_URL))
        
        layout.addWidget(self.browser)

    def on_news_loaded(self) -> None:
        # Keep this trigger alive for the parent manager navigation flow
        if hasattr(self, 'stackedWidget') and self.stackedWidget is not None:
            self.stackedWidget.setCurrentIndex(1)