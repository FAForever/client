from PyQt4 import QtCore, QtGui
import hashlib

import util
from config import Settings

FormClass, BaseClass = util.loadUiType("client/login.ui")

class LoginWidget(FormClass, BaseClass):
    def __init__(self, client):
        # TODO - init with the parent to inherit the stylesheet
        # once we make some of our own css to go with it
        BaseClass.__init__(self)
        self.setupUi(self)
        util.setStyleSheet(self, "client/login.css")
        self.splash.setPixmap(util.pixmap("client/login_watermark.png"))

        self.client = client
        if self.client.login:
            self.loginField.setText(self.client.login)

    @QtCore.pyqtSlot()
    def on_accepted(self):
        password = self.passwordField.text()
        hashed_password = hashlib.sha256(password.strip().encode("utf-8")).hexdigest()
        self.client.password = hashed_password
        # Else the client has a hashed password already
        # and the user didn't give us a different one

        self.client.login = self.loginField.text().strip()
        self.accept()

    @QtCore.pyqtSlot()
    def on_rejected(self):
        self.reject()

    @QtCore.pyqtSlot(bool)
    def on_remember_checked(self, checked):
        self.client.remember = checked

    @QtCore.pyqtSlot()
    def on_new_account(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(Settings.get("CREATE_ACCOUNT_URL")))

    @QtCore.pyqtSlot()
    def on_rename_account(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(Settings.get("NAME_CHANGE_URL")))

    @QtCore.pyqtSlot()
    def on_steamlink_account(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(Settings.get("STEAMLINK_URL")))

    @QtCore.pyqtSlot()
    def on_forgot_password(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(Settings.get("PASSWORD_RECOVERY_URL")))

    @QtCore.pyqtSlot()
    def on_bugreport(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(Settings.get("TICKET_URL")))
