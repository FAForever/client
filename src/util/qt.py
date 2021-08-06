import types

from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWebEngineWidgets import QWebEnginePage


class ExternalLinkPage(QWebEnginePage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.linkHovered.connect(self.saveHoveredLink)
        self.linkUnderCursor = ""

    def acceptNavigationRequest(self, url, navtype, isMainFrame):
        if navtype == QWebEnginePage.NavigationTypeLinkClicked:
            if url.toString() == self.linkUnderCursor:
                QDesktopServices.openUrl(url)
            return False
        return True

    def saveHoveredLink(self, url):
        self.linkUnderCursor = url


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


def monkeypatch_method(obj, name, fn):
    old_fn = getattr(obj, name)

    def wrapper(self, *args, **kwargs):
        return fn(self, old_fn, *args, **kwargs)
    setattr(obj, name, types.MethodType(wrapper, obj))
