from PyQt5 import QtCore, QtGui

import util
from config import Settings

FormClass, BaseClass = util.loadUiType("client/login.ui")

class LoginWidget(FormClass, BaseClass):
    finished = QtCore.pyqtSignal(str, str)
    remember = QtCore.pyqtSignal(bool)

    def __init__(self, startLogin = None, remember = False):
        # TODO - init with the parent to inherit the stylesheet
        # once we make some of our own css to go with it
        BaseClass.__init__(self)
        self.setupUi(self)
        util.setStyleSheet(self, "client/login.css")
        self.splash.setPixmap(util.pixmap("client/login_watermark.png"))

        if startLogin:
            self.loginField.setText(startLogin)
        self.rememberCheckbox.setChecked(remember)

    @QtCore.pyqtSlot()
    def on_accepted(self):
        password = self.passwordField.text()
        hashed_password = util.password_hash(password)
        login = self.loginField.text().strip()
        self.accept()
        self.finished.emit(login, hashed_password)

    @QtCore.pyqtSlot()
    def on_rejected(self):
        self.reject()

    @QtCore.pyqtSlot(bool)
    def on_remember_checked(self, checked):
        self.remember.emit(checked)

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
