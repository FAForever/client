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


def injectWebviewCSS(page, css):
    # Hacky way to inject CSS into QWebEnginePage, since QtWebengine doesn't
    # have a way to inject user CSS yet
    # We should eventually remove all QtWebEngine uses anyway
    js = """
        var css = document.createElement("style");
        css.type = "text/css";
        css.innerHTML = `{}`;
        document.head.appendChild(css);
        """
    js = js.format(css)
    page.runJavaScript(js)
