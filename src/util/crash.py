# Bug Reporting
import config
from config import Settings
from faf.api import BugReportSchema

CRASH_REPORT_USER = "pre-login"

import util

from . import APPDATA_DIR, PERSONAL_DIR, VERSION_STRING, LOG_FILE_FAF, \
    readlines

from PyQt4 import QtGui, QtCore
import traceback
import hashlib

from faf.domain.bugs import BugReport, BugReportTarget


class CrashDialog(QtGui.QDialog):
    def __init__(self, exc_info, *args, **kwargs):
        QtGui.QDialog.__init__(self, *args, **kwargs)

        exc_type, exc_value, traceback_object = exc_info

        dialog = self
        if kwargs.get('automatic'):
            automatic = True
        else:
            automatic = Settings.get('client/auto_bugreport', type=bool, default=True)

        self.trace = u"".join(traceback.format_exception(exc_type, exc_value, traceback_object, 10))

        self.title = u"Report from " + CRASH_REPORT_USER + u": " + str(exc_value)

        self.bugreport_target = BugReportTarget('client',
                                                'https://github.com/FAForever/client',
                                                config.VERSION)
        self.bugreport = BugReport(self.title,
                                   target=self.bugreport_target,
                                   traceback=self.trace)

        dialog.setWindowTitle(self.title)

        description = u""
        try:
            description += (u"\n**FAF Username:** " + CRASH_REPORT_USER)
            description += (u"\n**FAF Version:** " + VERSION_STRING)
            description += (u"\n**FAF Environment:** " + config.environment)
            description += (u"\n**FAF Directory:** " + APPDATA_DIR)
            description += (u"\n**FA Path:** " + str(util.settings.value("ForgedAlliance/app/path", None, type=str)))
            description += (u"\n**Home Directory:** " + PERSONAL_DIR)
        except StandardError:
            description += (u"\n**(Exception raised while writing debug vars)**")

        log = u""
        try:
            log += (u"\n".join(readlines(LOG_FILE_FAF, False)[-128:]))
        except StandardError:
            log += (unicode(LOG_FILE_FAF))
            log += (u"empty or not readable")

        self.bugreport.description = description
        self.bugreport.log = log

        if not automatic:
            self.box = QtGui.QTextEdit()
            self.box.setFont(QtGui.QFont("Lucida Console", 8))
            self.box.append(description)
            dialog.layout().addWidget(self.box)
            dialog.setLayout(QtGui.QVBoxLayout())
            label = QtGui.QLabel()
            label.setText("An error has occurred in the FAF client. <br><br>You can report it by clicking the ticket button.")
            label.setWordWrap(True)
            dialog.layout().addWidget(label)


            label = QtGui.QLabel()
            label.setText("<b>This is what happened. If you have more to add please write in the field below.</b>")
            label.setWordWrap(False)
            dialog.layout().addWidget(label)
            self.sendButton = QtGui.QPushButton("\nReport error\n")
            self.sendButton.pressed.connect(self.post_report)

            dialog.layout().addWidget(self.sendButton)

            label = QtGui.QLabel()
            label.setText("<b></b><br/><i>(please note that the error may be fatal, proceed at your own risk)</i>")
            label.setWordWrap(False)
            dialog.layout().addWidget(label)

            self.buttons = QtGui.QDialogButtonBox()
            buttons = self.buttons
            buttons.addButton("Continue", QtGui.QDialogButtonBox.AcceptRole)
            buttons.addButton("Close FAF", QtGui.QDialogButtonBox.RejectRole)
            buttons.addButton("Help", QtGui.QDialogButtonBox.HelpRole)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            buttons.helpRequested.connect(self.tech_support)
            dialog.layout().addWidget(buttons)
        else:
            dialog.setLayout(QtGui.QVBoxLayout())
            label = QtGui.QLabel()
            label.setText("An error has occurred in the FAF client. It has been automatically reported.")
            label.setWordWrap(True)
            dialog.layout().addWidget(label)
            self.post_report()
            self.sendButton = QtGui.QPushButton("\nOK\n")
            self.sendButton.pressed.connect(dialog.accept)
            dialog.layout().addWidget(self.sendButton)

    @QtCore.pyqtSlot()
    def tech_support(self):
        QtGui.QDesktopServices().openUrl(QtCore.QUrl(Settings.get("HELP_URL")))

    @QtCore.pyqtSlot()
    def post_report(self):
        # Be pessimistic here and import a new api client
        import faf.api.client
        c = faf.api.client.ApiClient()
        data, errors = BugReportSchema().dump(self.bugreport)
        c.post('/bugs', json=data)
