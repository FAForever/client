from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QObject
from util.select_player_dialog import SelectPlayerDialog, PlayerCompleter
from power.actions import BanPeriod


class CloseGameDialog(SelectPlayerDialog):
    def __init__(self, mod_actions, playerset, parent_widget):
        SelectPlayerDialog.__init__(self, playerset, parent_widget)
        self._mod_actions = mod_actions

    @classmethod
    def build(cls, mod_actions, playerset, parent_widget, **kwargs):
        return cls(mod_actions, playerset, parent_widget)

    def show(self, username=""):
        self.show_dialog("Closing player's game", "Player name:", username)

    def _at_value(self, name):
        if not self._mod_actions.close_fa(name):
            msg = QMessageBox(self._parent_widget)
            msg.setWindowTitle("Player not found!")
            msg.setText("The specified player was not found.")
            msg.show()


class KickDialog(QObject):
    def __init__(self, username, mod_actions, playerset, theme, parent_widget):
        QObject.__init__(self, parent_widget)
        self._mod_actions = mod_actions
        self._playerset = playerset
        self.set_theme(theme)
        self.form.leUsername.setText(username)
        self.base.show()

    @classmethod
    def builder(cls, mod_actions, playerset, theme, parent_widget, **kwargs):
        def make(username=""):
            return cls(username, mod_actions, playerset, theme, parent_widget)
        return make

    def set_theme(self, theme):
        formc, basec = theme.loadUiType("client/kick.ui")
        self.form = formc
        self.base = basec
        self.form.setupUi(self.base)

        self.form.cbBan.stateChanged.connect(self.banChanged)
        self.base.accepted.connect(self.accepted)
        self.base.rejected.connect(self.rejected)

        completer = PlayerCompleter(self._playerset, self.base)
        self.form.leUsername.setCompleter(completer)

    def banChanged(self, newState):
        checked = self.form.cbBan.isChecked()
        self.form.cbReason.setEnabled(checked)
        self.form.sbDuration.setEnabled(checked)
        self.form.cbPeriod.setEnabled(checked)

    def _warning(self, title, text):
        msg = QMessageBox(QMessageBox.Warning, title, text,
                          parent=self._parent_widget)
        msg.show()

    def accepted(self):
        username = self.form.leUsername.text()
        if not self.form.cbBan.isChecked():
            result = self._mod_actions.kick_player(username)
        else:
            reason = self.form.cbReason.currentText()
            duration = self.form.sbDuration.value()
            period = [e for e in BanPeriod][self.form.cbPeriod.currentIndex()]
            result = self._mod_actions.ban_player(username, reason, duration,
                                                  period)

        if not result:
            self._warning("Player not found",
                          'Player "{}" was not found.'.format(username))
        self.setParent(None)    # Let ourselves get GC'd

    def rejected(self):
        self.setParent(None)    # Let ourselves get GC'd


class PowerView:
    def __init__(self, close_game_dialog, kick_dialog):
        self.close_game_dialog = close_game_dialog
        self.kick_dialog = kick_dialog

    @classmethod
    def build(cls, **kwargs):
        close_game_dialog = CloseGameDialog.build(**kwargs)
        kick_dialog = KickDialog.builder(**kwargs)
        return cls(close_game_dialog, kick_dialog)
