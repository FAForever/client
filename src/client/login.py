import logging

from PyQt5 import QtCore, QtGui

import config
import util
from config import Settings
from config.production import default_values as main_environment
from config.testing import default_values as testing_environment

logger = logging.getLogger(__name__)

FormClass, BaseClass = util.THEME.loadUiType("client/login.ui")


class LoginWidget(FormClass, BaseClass):
    finished = QtCore.pyqtSignal(bool)
    request_quit = QtCore.pyqtSignal()
    remember = QtCore.pyqtSignal(bool)
    environments = dict(
        main=main_environment,
        test=testing_environment,
    )

    def __init__(self, remember=False):
        # TODO - init with the parent to inherit the stylesheet
        # once we make some of our own css to go with it
        BaseClass.__init__(self)
        self.setupUi(self)
        util.THEME.stylesheets_reloaded.connect(self.load_stylesheet)
        self.load_stylesheet()
        self.splash.setPixmap(util.THEME.pixmap("client/login_watermark.png"))

        self.rememberCheckbox.setChecked(remember)
        self.serverPortField.setValidator(QtGui.QIntValidator(1, 65535))
        self.replayServerPortField.setValidator(QtGui.QIntValidator(1, 65535))
        self.ircServerPortField.setValidator(QtGui.QIntValidator(1, 65535))
        self.populateEnvironments()

    def load_stylesheet(self):
        self.setStyleSheet(util.THEME.readstylesheet("client/login.css"))

    def populateEnvironments(self):
        for key, env in self.environments.items():
            self.environmentBox.addItem(env["display_name"], key)

    @QtCore.pyqtSlot()
    def on_toggle_extra_options(self):
        if self.extraOptionsFrame.isVisible():
            self.extraOptionsFrame.hide()
        else:
            self.extraOptionsFrame.show()

    @QtCore.pyqtSlot()
    def on_fill_extra_options(self):
        env = self.environmentBox.currentData()

        self.serverHostField.setText(self.environments[env]["lobby/host"])
        self.serverPortField.setText(str(self.environments[env]["lobby/port"]))

        self.replayServerHostField.setText(
            self.environments[env]["replay_server/host"],
        )
        self.replayServerPortField.setText(
            str(self.environments[env]["replay_server/port"]),
        )

        self.ircServerHostField.setText(self.environments[env]["chat/host"])
        self.ircServerPortField.setText(
            str(self.environments[env]["chat/port"]),
        )

        self.apiURLField.setText(self.environments[env]["api"])

    @QtCore.pyqtSlot()
    def on_accepted(self):
        host = self.serverHostField.text()
        port = int(self.serverPortField.text())
        replay_host = self.replayServerHostField.text().strip()
        replay_port = int(self.replayServerPortField.text())
        irc_host = self.ircServerHostField.text().strip()
        irc_port = int(self.ircServerPortField.text())
        api_url = self.apiURLField.text()

        logger.info(
            "Setting connection options: [server: {}:{}, IRC: {}:{}, "
            "replay_server: {}:{}, api_url: {}]".format(
                host, port, irc_host, irc_port,
                replay_host, replay_port, api_url,
            ),
        )

        Settings.set('lobby/host', host, persist=False)
        Settings.set('lobby/port', port, persist=False)
        Settings.set('chat/host', irc_host, persist=False)
        Settings.set('chat/port', irc_port, persist=False)
        Settings.set('replay_server/host', replay_host, persist=False)
        Settings.set('replay_server/port', replay_port, persist=False)
        api_changed = Settings.get('api') != api_url
        Settings.set('api', api_url, persist=False)
        config.defaults = self.environments[self.environmentBox.currentData()]
        self.accept()
        self.finished.emit(api_changed)

    @QtCore.pyqtSlot()
    def on_request_quit(self):
        self.request_quit.emit()
        self.reject()

    @QtCore.pyqtSlot(bool)
    def on_remember_checked(self, checked):
        self.remember.emit(checked)

    @QtCore.pyqtSlot()
    def on_new_account(self):
        QtGui.QDesktopServices.openUrl(
            QtCore.QUrl(Settings.get("CREATE_ACCOUNT_URL")),
        )

    @QtCore.pyqtSlot()
    def on_rename_account(self):
        QtGui.QDesktopServices.openUrl(
            QtCore.QUrl(Settings.get("NAME_CHANGE_URL")),
        )

    @QtCore.pyqtSlot()
    def on_steamlink_account(self):
        QtGui.QDesktopServices.openUrl(
            QtCore.QUrl(Settings.get("STEAMLINK_URL")),
        )

    @QtCore.pyqtSlot()
    def on_forgot_password(self):
        QtGui.QDesktopServices.openUrl(
            QtCore.QUrl(Settings.get("PASSWORD_RECOVERY_URL")),
        )

    @QtCore.pyqtSlot()
    def on_bugreport(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(Settings.get("TICKET_URL")))
