import logging

from PyQt5 import QtCore, QtGui, QtWebEngineWidgets

import util

logger = logging.getLogger(__name__)

FormClass, BaseClass = util.THEME.loadUiType("client/oauth.ui")


class OAuthWidget(FormClass, BaseClass):
    finished = QtCore.pyqtSignal(str, str, str)
    request_quit = QtCore.pyqtSignal()

    def __init__(self, oauth_state=None, url=None, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)
        self.setupUi(self)
        self.webview = QtWebEngineWidgets.QWebEngineView()
        self.layout().addWidget(self.webview)
        self.url = QtCore.QUrl(url)
        self.oauth_state = oauth_state
        self.webpage = OAuthWebPage()
        self.webpage.setUrl(self.url)
        self.webview.setPage(self.webpage)

        self.webpage.navigationRequestAccepted.connect(
            self.navigationRequestAccepted
        )

    def navigationRequestAccepted(self, url):
        query = QtCore.QUrlQuery(url)
        code = query.queryItemValue("code")
        state = query.queryItemValue("state")
        error = query.queryItemValue("error")
        if state and code:
            self.accept()
            if self.oauth_state == state:
                self.finished.emit(state, code, error)
            else:
                self.finished.emit("", "", "")
        elif error:
            self.reject()
            self.finished.emit("", "", error)


class OAuthWebPage(QtWebEngineWidgets.QWebEnginePage):
    navigationRequestAccepted = QtCore.pyqtSignal(QtCore.QUrl)

    def __init__(self):
        QtWebEngineWidgets.QWebEnginePage.__init__(self)

    def acceptNavigationRequest(self, url, type_, isMainFrame):
        if "oauth" in url.url() or "localhost" in url.url():
            self.navigationRequestAccepted.emit(url)
            return True
        elif type_ == 1:
            return False
        else:
            QtGui.QDesktopServices.openUrl(url)
            return False
