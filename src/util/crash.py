# -------------------------------------------------------------------------------
# Copyright (c) 2012 Gael Honorez.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# -------------------------------------------------------------------------------


# Bug Reporting
CRASH_REPORT_USER = "pre-login"

import util

from . import APPDATA_DIR, PERSONAL_DIR, VERSION_STRING, LOG_FILE_FAF, \
    readlines

from PyQt4 import QtGui, QtCore
import traceback
import hashlib

HELP_URL = "http://forums.faforever.com/forums/viewforum.php?f=3"
TICKET_URL = "https://github.com/FAForever/lobby/issues"

class CrashDialog(QtGui.QDialog):
    def __init__(self, exc_info, *args, **kwargs):
        QtGui.QDialog.__init__(self, *args, **kwargs)

        exc_type, exc_value, traceback_object = exc_info

        dialog = self

        dialog.setLayout(QtGui.QVBoxLayout())
        label = QtGui.QLabel()
        label.setText("An Error has occurred in FAF.<br><br>You can report it by clicking the ticket button.\
                        <b>Please check if that error is new first !</b>")
        label.setWordWrap(True)
        dialog.layout().addWidget(label)

        label = QtGui.QLabel()
        label.setText("<b>This is what happened (but please add your own explanation !)</b>")
        label.setWordWrap(False)
        dialog.layout().addWidget(label)

        self.trace = u"".join(traceback.format_exception(exc_type, exc_value, traceback_object, 10))
        self.hash = hashlib.md5(self.trace).hexdigest()

        self.title = u"[auto] Crash from " + CRASH_REPORT_USER + u": " + str(exc_value)

        dialog.setWindowTitle(self.title)

        self.box = QtGui.QTextEdit()
        box = self.box
        try:
            box.setFont(QtGui.QFont("Lucida Console", 8))
            box.append(u"\n**FAF Username:** " + CRASH_REPORT_USER)
            box.append(u"\n**FAF Version:** " + VERSION_STRING)
            box.append(u"\n**FAF Directory:** " + APPDATA_DIR)
            box.append(u"\n**FA Path:** " + str(util.settings.value("ForgedAlliance/app/path", None, type=str)))
            box.append(u"\n**Home Directory:** " + PERSONAL_DIR)
        except StandardError:
            box.append(u"\n**(Exception raised while writing debug vars)**")
            pass

        box.append(u"")
        box.append(u"\n**FA Forever Log (last 128 lines):**")
        box.append(u"{{{")
        try:
            box.append("\n".join(readlines(LOG_FILE_FAF, False)[-128:]))
        except StandardError:
            box.append(unicode(LOG_FILE_FAF))
            box.append(u"empty or not readable")

        box.append(u"\n**Stack trace:**")
        box.append(u"{{{")
        box.append(self.trace)
        box.append(u"}}}")
        box.append(u"")

        dialog.layout().addWidget(box)
        self.sendButton = QtGui.QPushButton("\nOpen ticket system.\n")
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

    @QtCore.pyqtSlot()
    def tech_support(self):
        QtGui.QDesktopServices().openUrl(QtCore.QUrl(HELP_URL))

    @QtCore.pyqtSlot()
    def post_report(self):
        QtGui.QDesktopServices().openUrl(QtCore.QUrl(TICKET_URL))
