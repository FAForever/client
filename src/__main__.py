#!/usr/bin/env python3
"""
Created on Dec 1, 2011

@author: thygrrr
"""

# CRUCIAL: This must remain on top.
#import sip

#sip.setapi('QString', 2)
#sip.setapi('QVariant', 2)
#sip.setapi('QStringList', 2)
#sip.setapi('QList', 2)
#sip.setapi('QProcess', 2)

import os
import sys

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

if sys.platform == 'win32':
    os.environ.setdefault('QT_OPENGL', 'angle')
    os.environ.setdefault('QT_ANGLE_PLATFORM', 'd3d9')

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import Qt

path = os.path.join(os.path.dirname(sys.argv[0]), "PyQt5.uic.widget-plugins")
uic.widgetPluginPath.append(path)

# According to PyQt5 docs we need to import this before we create QApplication
from PyQt5 import QtWebEngineWidgets

import util

# Set up crash reporting
excepthook_original = sys.excepthook


def excepthook(exc_type, exc_value, traceback_object):
    """
    This exception hook will stop the app if an uncaught error occurred, regardless where in the QApplication.
    """
    sys.excepthook = excepthook_original

    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, traceback_object))
    logger.error("Runtime Info:\n%s", util.runtime_info())
    dialog = util.CrashDialog((exc_type, exc_value, traceback_object))
    answer = dialog.exec_()

    if answer == QtWidgets.QDialog.Rejected:
        QtWidgets.QApplication.exit(1)

    sys.excepthook = excepthook


def AdminUserErrorDialog():
    from config import Settings
    ignore_admin = Settings.get("client/ignore_admin", False, bool)
    if not ignore_admin:
        box = QtWidgets.QMessageBox()
        box.setText("FAF should not be run as an administrator!<br><br>This probably means you need "
                    "to fix the file permissions in C:\\ProgramData.<br>Proceed at your own risk.")
        box.setStandardButtons(QtWidgets.QMessageBox.Ignore | QtWidgets.QMessageBox.Close)
        box.setIcon(QtWidgets.QMessageBox.Critical)
        box.setWindowTitle("FAF privilege error")
        if box.exec_() == QtWidgets.QMessageBox.Ignore:
            Settings.set("client/ignore_admin", True)


def runFAF():
    # Load theme from settings (one of the first things to be done)
    util.THEME.loadTheme()

    # Create client singleton and connect
    import client

    faf_client = client.instance
    faf_client.setup()
    faf_client.show()
    faf_client.doConnect()

    # Main update loop
    QtWidgets.QApplication.exec_()

if __name__ == '__main__':
    import logging
    import config

    QtWidgets.QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QtWidgets.QApplication(sys.argv)

    if sys.platform == 'win32':
        import platform
        import ctypes
        if platform.release() != "XP":  # legacy special :-)
            if config.admin.isUserAdmin():
                AdminUserErrorDialog()

        if getattr(ctypes.windll.shell32, "SetCurrentProcessExplicitAppUserModelID", None) is not None:
            myappid = 'com.faforever.lobby'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    logger = logging.getLogger(__name__)
    logger.info(">>> --------------------------- Application Launch")

    # Set application icon to nicely stack in the system task bar
    app.setWindowIcon(util.THEME.icon("window_icon.png", True))

    # We can now set our excepthook since the app has been initialized
    sys.excepthook = excepthook

    if len(sys.argv) == 1:
        # Do the magic
        sys.path += ['.']
        runFAF()
    else:
        # Try to interpret the argument as a replay.
        if sys.argv[1].lower().endswith(".fafreplay") or sys.argv[1].lower().endswith(".scfareplay"):
            import fa
            fa.replay(sys.argv[1], True)  # Launch as detached process

    # End of show
    app.closeAllWindows()
    app.quit()

    # End the application, perform some housekeeping
    logger.info("<<< --------------------------- Application Shutdown")
