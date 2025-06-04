"""
Created on Dec 1, 2011

@author: thygrrr
"""

import argparse
import os
import sys
from types import TracebackType

from PyQt6 import uic
from PyQt6.QtCore import QPointF
from PyQt6.QtCore import QRectF
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import QSplashScreen
from PyQt6.QtWidgets import QStyleFactory

from src import util
from src.config import Settings
from src.config.version import get_release_version
from src.util import crash

if os.getenv("XDG_SESSION_TYPE") == "wayland":
    # clientwindow has FramelessWindowHint flag with custom frame implementation,
    # which doesn't work well with 'wayland'
    os.environ["QT_QPA_PLATFORM"] = "xcb"

# Some linux distros (like Gentoo) make package scripts available
# by copying and modifying them. This breaks path to our modules.

if __package__ is None and not hasattr(sys, 'frozen'):
    # We are run by the interpreter. Are we run from source?
    file_dir = os.path.dirname(os.path.realpath(__file__))
    base_dir = os.path.basename(file_dir)
    if base_dir != 'src':
        # We're probably run as an installed file.
        import fafclient
        path = os.path.realpath(fafclient.__file__)
        sys.path.insert(0, os.path.dirname(path))


cmd_parser = argparse.ArgumentParser(
    description='FAF client commandline arguments.',
)

args, trailing_args = cmd_parser.parse_known_args()


path = os.path.join(os.path.dirname(sys.argv[0]), "PyQt6.uic.widget-plugins")
uic.widgetPluginPath.append(path)

# Set up crash reporting
excepthook_original = sys.excepthook


def excepthook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        traceback_object: TracebackType | None,
) -> None:
    """
    This exception hook will stop the app if an uncaught error occurred,
    regardless where in the QApplication.
    """
    sys.excepthook = excepthook_original
    if exc_type is KeyboardInterrupt:
        raise exc_value

    logger.error(
        "Uncaught exception",
        exc_info=(
            exc_type, exc_value,
            traceback_object,
        ),
    )
    logger.error("Runtime Info:\n%s", crash.runtime_info())
    dialog = crash.CrashDialog((exc_type, exc_value, traceback_object))
    answer = dialog.exec()

    if answer == QDialog.DialogCode.Rejected:
        QApplication.exit(1)

    sys.excepthook = excepthook


def admin_user_error_dialog() -> None:
    ignore_admin = Settings.get("client/ignore_admin", False, bool)
    if not ignore_admin:
        box = QMessageBox()
        box.setText(
            "FAF should not be run as an administrator!<br><br>This "
            "probably means you need to fix the file permissions in "
            "C:\\ProgramData.<br>Proceed at your own risk.",
        )
        box.setStandardButtons(QMessageBox.StandardButton.Ignore | QMessageBox.StandardButton.Close)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("FAF privilege error")
        if box.exec() == QMessageBox.StandardButton.Ignore:
            Settings.set("client/ignore_admin", True)


def show_splash_screen_message(splash: QSplashScreen, message: str) -> None:
    splash.showMessage(
        message,
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
        Qt.GlobalColor.darkYellow,
    )


def run_faf(app: QApplication, splash: QSplashScreen) -> None:
    # Load theme from settings (one of the first things to be done)
    util.THEME.loadTheme()

    # Create client singleton and connect
    show_splash_screen_message(splash, "Loading required modules...")
    from src import client

    faf_client = client.instance

    show_splash_screen_message(splash, "Initializing...")
    faf_client.setup()
    faf_client.show()
    splash.finish(faf_client)

    faf_client.try_to_auto_login()

    # Main update loop
    QApplication.exec()


def set_style(app: QApplication) -> None:
    styles = QStyleFactory.keys()
    preferred_style = Settings.get("theme/style", "windowsvista")
    if preferred_style in styles:
        app.setStyle(QStyleFactory.create(preferred_style))


def draw_version_on_splash_screen(pixmap: QPixmap) -> None:
    painter = QPainter(pixmap)

    font = painter.font()
    font.setPointSize(11)
    font.setBold(True)
    painter.setFont(font)

    painter.setPen(Qt.GlobalColor.darkYellow)

    version = get_release_version(util.THEME.theme.themedir)

    font_metrics = painter.fontMetrics()
    version_rect = QRectF(0, 0, font_metrics.horizontalAdvance(version), font_metrics.height())
    bottom_right = QPointF(pixmap.width() - 10, pixmap.height() - 5)
    version_rect.moveBottomRight(bottom_right)

    painter.drawText(version_rect, version)


def get_splash_screen_pixmap() -> QPixmap:
    pixmap = util.THEME.pixmap("splash_screen.png")
    # makes this function 2x slower, but nice to have
    draw_version_on_splash_screen(pixmap)
    return pixmap


def create_splash_screen() -> QSplashScreen:
    splash = QSplashScreen(get_splash_screen_pixmap())
    splash_font = splash.font()
    splash_font.setPointSize(11)
    splash.setFont(splash_font)
    return splash


if __name__ == '__main__':
    import logging

    from src import config

    app = QApplication(["FAF Python Client"] + trailing_args)

    splash = create_splash_screen()
    splash.show()

    set_style(app)

    if sys.platform == 'win32':
        import ctypes
        import platform
        if platform.release() != "XP":  # legacy special :-)
            if config.admin.isUserAdmin():
                admin_user_error_dialog()

        attribute = getattr(
            ctypes.windll.shell32,
            "SetCurrentProcessExplicitAppUserModelID",
            None,
        )
        if attribute is not None:
            myappid = 'com.faforever.lobby'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                myappid,
            )

    logger = logging.getLogger(__name__)
    logger.info(">>> --------------------------- Application Launch")

    # Set application icon to nicely stack in the system task bar
    app.setWindowIcon(util.THEME.icon("window_icon.png", True))

    # We can now set our excepthook since the app has been initialized
    sys.excepthook = excepthook

    if len(trailing_args) == 0:
        run_faf(app, splash)
    else:
        # Try to interpret the argument as a replay.
        if (
            trailing_args[0].lower().endswith(".fafreplay")
            or trailing_args[0].lower().endswith(".scfareplay")
        ):
            from src import fa
            fa.replay(trailing_args[0], True)  # Launch as detached process

    # End of show
    app.closeAllWindows()
    app.deleteLater()
    app.quit()

    # End the application, perform some housekeeping
    logger.info("<<< --------------------------- Application Shutdown")
