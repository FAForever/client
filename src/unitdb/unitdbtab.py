import logging

from PyQt5.QtCore import QObject, QUrl, pyqtSignal
from PyQt5.QtNetwork import QNetworkCookie
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineProfile

import util
from config import Settings
from ui.busy_widget import BusyWidget

logger = logging.getLogger(__name__)

FormClass, BaseClass = util.THEME.loadUiType("unitdb/unitdb.ui")


class UnitDbView(FormClass, BaseClass, BusyWidget):
    entered = pyqtSignal()

    def __init__(self):
        super(BaseClass, self).__init__()
        BusyWidget.__init__(self)
        self.setupUi(self)

        # Isolate profile so we only grab cookies from unitdb
        self._page_profile = QWebEngineProfile()
        self.unitdbWebView.setPage(QWebEnginePage(self._page_profile))

    def busy_entered(self):
        self.entered.emit()


class UnitDBTab:
    def __init__(self, db_widget, cookie_store):
        self.db_widget = db_widget
        self._cookie_store = cookie_store
        self._db_url = Settings.get("UNITDB_URL")
        self._db_url_alt = Settings.get("UNITDB_SPOOKY_URL")
        self._current_cookie = CurrentCookie(self._qt_cookie_store,
                                             b"unitDB-settings")
        self._current_cookie.new_cookie.connect(self._new_cookie)

        self.alternativeDB = Settings.get('unitDB/alternative', type=bool, default=False)
        self._first_entered = True
        self.db_widget.entered.connect(self.entered)
        self.db_widget.fafDbButton.pressed.connect(self.open_default_tab)
        self.db_widget.spookyDbButton.pressed.connect(self.open_alternative_tab)
    @property
    def _db_view(self):
        return self.db_widget.unitdbWebView

    @property
    def _qt_cookie_store(self):
        return self._db_view.page().profile().cookieStore()

    def _load_settings(self):
        qt_store = self._qt_cookie_store
        try:
            for cookie in self._cookie_store.load_cookie():
                qt_store.setCookie(cookie)
        except (IOError, FileNotFoundError) as e:
            logger.warning("Failed to load unitdb settings: {}".format(e))

    def _save_settings(self):
        self._cookie_store.save_cookie(self._current_cookie.cookie)

    def _new_cookie(self):
        try:
            self._save_settings()
        except IOError as e:
            logger.warning("Failed to save unitdb settings: {}".format(e))

    def entered(self):
        if self._first_entered:
            self._first_entered = False
            self._load_settings()

            if self.alternativeDB:
                self._db_view.setUrl(QUrl(self._db_url_alt))
            else:
                self._db_view.setUrl(QUrl(self._db_url))

    def open_default_tab(self):
        if self.alternativeDB:
            self.alternativeDB = False
            Settings.set('unitDB/alternative', False)
        self._db_view.setUrl(QUrl(self._db_url))

    def open_alternative_tab(self):
        if not self.alternativeDB:
            self.alternativeDB = True
            Settings.set('unitDB/alternative', True)
        self._db_view.setUrl(QUrl(self._db_url_alt))

class UnitDBCookieStorage:
    def __init__(self, store_file):
        self._store_file = store_file

    def load_cookie(self):
        with open(self._store_file, 'rb+') as store:
            cookies = store.read()
            return QNetworkCookie.parseCookies(cookies)

    def save_cookie(self, cookie):
        with open(self._store_file, 'wb+') as store:
            store.write(cookie + b'\n' if cookie is not None else b'')


class CurrentCookie(QObject):
    new_cookie = pyqtSignal()

    def __init__(self, source, filter_bytes=None):
        QObject.__init__(self)
        self._source = source
        self._filter_bytes = filter_bytes
        self.cookie = None
        self._source.cookieAdded.connect(self._cookie_added)

    def _cookie_added(self, cookie):
        raw = cookie.toRawForm()
        if self._filter_bytes is None or self._filter_bytes in raw:
            self.cookie = raw
        self.new_cookie.emit()


def build_db_tab(store_file):
    db_view = UnitDbView()
    storage = UnitDBCookieStorage(store_file)
    return UnitDBTab(db_view, storage)
