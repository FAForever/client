from PyQt5 import QtCore, QtWidgets, QtGui

from PyQt5.QtWidgets import QCompleter

import util
import logging

logger = logging.getLogger(__name__)

FormClass, BaseClass = util.THEME.loadUiType("client/kick.ui")

class KickDialog(FormClass, BaseClass):
    PERIOD = ['HOUR', 'DAY', 'WEEK', 'MONTH', 'YEAR']

    def __init__(self, client, *args, **kwargs):
        BaseClass.__init__(self, client, *args, **kwargs)

        self.client = client

        self.setParent(client)

        self.setupUi(self)
        self.setModal(True)
        self.cbBan.stateChanged.connect(self.banChanged)
        self.buttonBox.accepted.connect(self.accepted)
        self.buttonBox.rejected.connect(self.rejected)

    def reset(self, name=""):
        self.leUsername.setText(name)
        self.cbBan.setChecked(False)
        self.cbReason.setEnabled(False)
        self.cbReason.setCurrentIndex(0)
        self.sbDuration.setEnabled(False)
        self.sbDuration.setValue(1)
        self.cbPeriod.setEnabled(False)
        self.cbPeriod.setCurrentIndex(1)

        online_players = [p.login for p in self.client.players]
        completer = QCompleter(online_players, self)
        self.leUsername.setCompleter(completer)

    def banChanged(self, newState):
        checked = self.cbBan.isChecked()
        self.cbReason.setEnabled(checked)
        self.sbDuration.setEnabled(checked)
        self.cbPeriod.setEnabled(checked)

    def accepted(self):
        username = self.leUsername.text()
        logger.info('closeLobby for {}'.format(username))

        user_id = self.client.players.getID(username)
        if user_id != -1:
            message = dict(command="admin", action="closelobby", user_id=user_id)
            if self.cbBan.isChecked():
                reason = self.cbReason.currentText()
                duration = self.sbDuration.value()
                period = self.PERIOD[self.cbPeriod.currentIndex()]

                message['ban'] = dict(reason=reason, duration=duration, period=period)
            self.client.lobby_connection.send(message)
            self.hide()
        else:
            QtWidgets.QMessageBox.warning(
                self,
                "User cannot be found",
                "User {} is not online as far as I can tell - did you typo the name?".format(username))

    def rejected(self):
        self.hide()



