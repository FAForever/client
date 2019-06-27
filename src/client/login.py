from PyQt5 import QtCore, QtGui, QtWidgets

import util
from config import Settings

FormClass, BaseClass = util.THEME.loadUiType("client/login.ui")


class LoginWidget(FormClass, BaseClass):
    finished = QtCore.pyqtSignal(str, str, str, int, str)
    request_quit = QtCore.pyqtSignal()
    remember = QtCore.pyqtSignal(bool)

    # TODO: Extract to JSON file
    environments = {
        "main": {
            "display": "Main Server (recommended)",
            "host": "lobby.faforever.com",
            "port": 8001,
            "api_url": "https://api.faforever.com"
        },
        "test": {
            "display": "Test Server",
            "host": "lobby.test.faforever.com",
            "port": 8001,
            "api_url": "http://api.test.faforever.com"
        }
    }

    def __init__(self, parent, startLogin=None, remember=False):
        # TODO - init with the parent to inherit the stylesheet
        # once we make some of our own css to go with it
        BaseClass.__init__(self, parent)
        self.setupUi(self)
        util.THEME.stylesheets_reloaded.connect(self.load_stylesheet)
        self.load_stylesheet()
        self.splash.setPixmap(util.THEME.pixmap("client/login_watermark.png"))

        if startLogin:
            self.loginField.setText(startLogin)
        self.rememberCheckbox.setChecked(remember)
        self.portField.setValidator(QtGui.QIntValidator(1, 65535))
        self.populateEnvironments()

    def load_stylesheet(self):
        self.setStyleSheet(util.THEME.readstylesheet("client/login.css"))

    def populateEnvironments(self):
        for k, env in self.environments.items():
            self.environmentBox.addItem(env["display"], k)

    @QtCore.pyqtSlot()
    def on_toggle_extra_options(self):
        if self.extraOptionsFrame.isVisible():
            self.extraOptionsFrame.hide()
        else:
            self.extraOptionsFrame.show()

    @QtCore.pyqtSlot()
    def on_fill_extra_options(self):
        env = self.environmentBox.currentData()
        self.hostField.setText(self.environments[env]["host"])
        self.portField.setText(str(self.environments[env]["port"]))
        self.apiURLField.setText(self.environments[env]["api_url"])

    @QtCore.pyqtSlot()
    def on_accepted(self):
        password = self.passwordField.text()
        hashed_password = util.password_hash(password)
        login = self.loginField.text().strip()
        host = self.hostField.text()
        port = int(self.portField.text())
        api_url = self.apiURLField.text()

        self.accept()
        self.finished.emit(login, hashed_password, host, port, api_url)

    @QtCore.pyqtSlot()
    def on_request_quit(self):
        self.request_quit.emit()
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
