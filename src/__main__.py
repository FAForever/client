"""
Created on Dec 1, 2011

@author: thygrrr
"""

# CRUCIAL: This must remain on top.
import sip

sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
sip.setapi('QStringList', 2)
sip.setapi('QList', 2)
sip.setapi('QProcess', 2)

import os
import sys

if os.path.isdir("lib"):
    sys.path.insert(0, os.path.abspath("lib"))
elif os.path.isdir("../lib"):
    sys.path.insert(0, os.path.abspath("../lib"))

from PyQt4 import QtGui, uic

path = os.path.join(os.path.dirname(sys.argv[0]), "PyQt4.uic.widget-plugins")
uic.widgetPluginPath.append(path)

# Are we running from a frozen interpreter?
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))
else:
    if sys.platform == 'win32':
        # We are most likely running from source
        srcDir = os.path.dirname(os.path.relpath(__file__))
        devRoot = os.path.abspath(os.path.join(srcDir, os.pardir))
        os.chdir(devRoot)
        # We need to set the working directory correctly.

import util
if sys.platform == 'win32':
    util.COMMON_DIR = os.path.join(os.getcwd(), "res")

# Set up crash reporting
excepthook_original = sys.excepthook

def excepthook(exc_type, exc_value, traceback_object):
    """
    This exception hook will stop the app if an uncaught error occurred, regardless where in the QApplication.
    """
    sys.excepthook = excepthook_original

    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, traceback_object))
    dialog = util.CrashDialog((exc_type, exc_value, traceback_object))
    answer = dialog.exec_()

    if answer == QtGui.QDialog.Rejected:
        QtGui.QApplication.exit(1)

    sys.excepthook = excepthook

def AdminUserErrorDialog():
    box = QtGui.QMessageBox()
    box.setText("FAF cannot be run as an administrator!")
    box.setStandardButtons(QtGui.QMessageBox.Close)
    box.setIcon(QtGui.QMessageBox.Critical)
    box.setWindowTitle("FAF privilege error")
    box.exec_()


def runFAF():
    # Load theme from settings (one of the first things to be done)
    util.loadTheme()

    # Create client singleton and connect
    import client

    faf_client = client.instance
    faf_client.setup()

    if not faf_client.doConnect():
        return

    faf_client.doLogin()
    faf_client.show()
    # Main update loop
    QtGui.QApplication.exec_()

if __name__ == '__main__':
    import platform
    import logging

    app = QtGui.QApplication(sys.argv)

    if platform.system() == "Windows":
        import ctypes
        if platform.release() != "XP":  # legacy special :-)
            if ctypes.windll.shell32.IsUserAnAdmin():
                AdminUserErrorDialog()
                app.quit()
                exit()

        if getattr(ctypes.windll.shell32, "SetCurrentProcessExplicitAppUserModelID", None) is not None:
            myappid = 'com.faforever.lobby'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


    logger = logging.getLogger(__name__)
    logger.info(">>> --------------------------- Application Launch")

    # Set application icon to nicely stack in the system task bar
    app.setWindowIcon(util.icon("window_icon.png", True))

    # We can now set our excepthook since the app has been initialized
    sys.excepthook = excepthook


    if len(sys.argv) == 1:
        #Do the magic
        sys.path += ['.']
        runFAF()
    else:
        # Try to interpret the argument as a replay.
        if sys.argv[1].lower().endswith(".fafreplay") or sys.argv[1].lower().endswith(".scfareplay"):
            from . import fa
            fa.replay(sys.argv[1], True)  # Launch as detached process

    #End of show
    app.closeAllWindows()
    app.quit()

    #End the application, perform some housekeeping
    logger.info("<<< --------------------------- Application Shutdown")

