# Bug Reporting
import config
import traceback
import util
from config import Settings
import platform

from . import APPDATA_DIR, PERSONAL_DIR, VERSION_STRING

from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl

CRASH_REPORT_USER = "pre-login"

FormClass, BaseClass = util.THEME.loadUiType("client/crash.ui")

def runtime_info():
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
        desc.append(("Platform", platform.platform()))
        desc.append(("Uname", str(platform.uname())))

        desc = "".join(["{}: {}\n".format(n, d) for n, d in desc])
    except Exception:
        desc = "(Exception raised while writing runtime info)\n"

    return desc

class CrashDialog(FormClass, BaseClass):
    def __init__(self, exc_info, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)
        self.setupUi(self)

        trace = "".join(traceback.format_exception(*exc_info, limit=10))

        desc = runtime_info()

        self.logField.setText("{}\nRuntime info:\n\n{}".format(trace, desc))

        self.helpButton.clicked.connect(self.tech_support)
        self.continueButton.clicked.connect(self.accept)
        self.quitButton.clicked.connect(self.reject)
        self.add_theme_caveat()

    def tech_support(self):
        QDesktopServices().openUrl(QUrl(Settings.get("SUPPORT_URL")))

    def add_theme_caveat(self):
        text = self.infoBlurb.text()
        try:
            config_loc = "(located at {}) ".format(util.Settings.fileName())
        except Exception:
            config_loc = ""
        text += ("<br><br><b>If you're seeing this message after overiding "
                 "an obsolete theme, go to the client config file {}and "
                 "remove the [theme_version_override] section.</b>").format(
                    config_loc)
        self.infoBlurb.setText(text)
