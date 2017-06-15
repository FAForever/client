from PyQt5.QtWebEngineWidgets import QWebEnginePage
from PyQt5.QtGui import QDesktopServices


class ExternalLinkPage(QWebEnginePage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def acceptNavigationRequest(self, url, navtype, isMainFrame):
        if navtype == QWebEnginePage.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(url)
            return False
        return True
