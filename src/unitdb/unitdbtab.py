from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from src import util
from src.config import Settings

FormClass, BaseClass = util.THEME.loadUiType("unitdb/unitdb.ui")


class UnitDbView(FormClass, BaseClass):
    def __init__(self) -> None:
        super(BaseClass, self).__init__()
        self.setupUi(self)


class UnitDBTab:
    def __init__(self) -> None:
        self.db_widget = UnitDbView()
        self._db_urls = (
            QUrl(Settings.get("UNITDB_URL")),
            QUrl(Settings.get("UNITDB_SPOOKY_URL")),
        )
        self.db_widget.fafDbButton.pressed.connect(lambda: self.open_db_url(0))
        self.db_widget.spookyDbButton.pressed.connect(lambda: self.open_db_url(1))

    def open_db_url(self, index: int, /) -> None:
        QDesktopServices.openUrl(self._db_urls[index])
