# Bug Reporting
import config
import traceback
import util
from config import Settings

from . import APPDATA_DIR, PERSONAL_DIR, VERSION_STRING

from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl

CRASH_REPORT_USER = "pre-login"

FormClass, BaseClass = util.loadUiType("client/crash.ui")

class CrashDialog(FormClass, BaseClass):
    def __init__(self, exc_info, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)
        self.setupUi(self)

        trace = "".join(traceback.format_exception(*exc_info, limit=10))

        try:
            desc = []
            desc.append(("FAF Username", CRASH_REPORT_USER))
            desc.append(("FAF Version", VERSION_STRING))
            desc.append(("FAF Environment", config.environment))
            desc.append(("FAF Directory", APPDATA_DIR))
            fa_path = util.settings.value("ForgedAlliance/app/path",
                                          "Unknown",
                                          type=str)
            desc.append(("FA Path: ", fa_path))
            desc.append(("Home Directory", PERSONAL_DIR))

            desc = "".join(["{}: {}\n".format(n, d) for n, d in desc])
        except Exception:
            desc = "(Exception raised while writing runtime info)\n"

        self.logField.setText("{}\nRuntime info:\n\n{}".format(trace, desc))

        self.helpButton.clicked.connect(self.tech_support)
        self.continueButton.clicked.connect(self.accept)
        self.quitButton.clicked.connect(self.reject)

    def tech_support(self):
        QDesktopServices().openUrl(QUrl(Settings.get("SUPPORT_URL")))
