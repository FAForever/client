# Bug Reporting
import platform
import traceback

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from src import config
from src import util
from src.config import Settings

CRASH_REPORT_USER = "pre-login"

FormClass, BaseClass = util.THEME.loadUiType("client/crash.ui")


def runtime_info() -> str:
    try:
        desc = []
        desc.append(("FAF Username", CRASH_REPORT_USER))
        desc.append(("FAF Version", util.VERSION_STRING))
        desc.append(("FAF Environment", config.environment))
        desc.append(("FAF Directory", util.APPDATA_DIR))
        fa_path = util.settings.value(
            "ForgedAlliance/app/path",
            "Unknown",
            type=str,
        )
        desc.append(("FA Path: ", fa_path))
        desc.append(("Home Directory", util.PERSONAL_DIR))
        desc.append(("Vaults Directory", util.VAULTS_BASE_DIR))
        desc.append(("Platform", platform.platform()))
        desc.append(("Uname", str(platform.uname())))

        desc = "".join([f"{n}: {d}\n" for n, d in desc])
    except Exception as e:
        desc = f"(Exception raised while writing runtime info: {e})\n"

    return desc


class CrashDialog(FormClass, BaseClass):
    def __init__(self, exc_info, *args, **kwargs):
        BaseClass.__init__(self, *args, **kwargs)
        self.setupUi(self)

        trace = "".join(traceback.format_exception(*exc_info, limit=10))

        desc = runtime_info()

        self.logField.setText(f"{trace}\nRuntime info:\n\n{desc}")

        self.helpButton.clicked.connect(self.tech_support)
        self.continueButton.clicked.connect(self.accept)
        self.quitButton.clicked.connect(self.reject)
        self.add_theme_caveat()

    def tech_support(self):
        QDesktopServices().openUrl(QUrl(Settings.get("SUPPORT_URL")))

    def add_theme_caveat(self):
        text = self.infoBlurb.text()
        try:
            config_loc = f"(located at {util.Settings.fileName()}) "
        except Exception:
            config_loc = ""
        text += (
            "<br><br><b>If you're seeing this message after overiding "
            "an obsolete theme, go to the client config file {}and "
            "remove the [theme_version_override] section.</b>"
            .format(config_loc)
        )
        self.infoBlurb.setText(text)
