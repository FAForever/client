from PyQt5.QtWidgets import QInputDialog, QLineEdit, QCompleter


class SelectPlayerDialog:
    def __init__(self, playerset, parent_widget):
        self._playerset = playerset
        self._parent_widget = parent_widget

    def show_dialog(self, title, label, name):
        dialog = QInputDialog(self._parent_widget)
        dialog.setInputMode(QInputDialog.TextInput)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        dialog.textValueSelected.connect(self._at_value)
        dialog.show()

        completer = PlayerCompleter(self._playerset, dialog)
        dialog.findChild(QLineEdit).setCompleter(completer)

    def _at_value(self, value):
        pass


class PlayerCompleter(QCompleter):
    def __init__(self, playerset, parent_widget):
        online_players = [p.login for p in playerset.values()]
        QCompleter.__init__(self, online_players, parent_widget)
