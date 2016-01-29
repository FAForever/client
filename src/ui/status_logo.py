from PyQt4.QtCore import pyqtSignal
from PyQt4.QtGui import QLabel, QAction, QMenu
import util
from client import ClientState


class StatusLogo(QLabel):
    disconnect_requested = pyqtSignal()
    reconnect_requested = pyqtSignal()
    about_dialog_requested = pyqtSignal()
    connectivity_dialog_requested = pyqtSignal()

    def __init__(self, client, logo_file='window_icon.png'):
        QLabel.__init__(self)

        self.state = client.state
        self.setScaledContents(True)
        self.setMargin(3)

        normal, yellow, red = map(util.pixmap, [
            'window_icon.png',
            'window_icon_yellow.png',
            'window_icon_red.png'
        ])

        self._pixmaps = {
            ClientState.ONLINE: normal,
            ClientState.ACCEPTED: yellow,
            ClientState.CREATED: yellow,
            ClientState.RECONNECTING: yellow,
            ClientState.DROPPED: yellow,
            ClientState.DISCONNECTED: red,
            ClientState.NONE: red
        }
        self.setMaximumSize(30, 30)

        client.state_changed.connect(self.change_state)
        self.change_state(client.state)

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        dc = QAction('Disconnect', None)
        rc = QAction('Reconnect', None)
        about = QAction('About', None)

        if self.state != ClientState.DISCONNECTED:
            menu.addAction(dc)
        if self.state != ClientState.ONLINE\
            and self.state != ClientState.RECONNECTING:
            menu.addAction(rc)

        menu.addAction(about)

        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action == dc:
            self.disconnect_requested.emit()
        elif action == rc:
            self.reconnect_requested.emit()
        elif action == about:
            self.about_dialog_requested.emit()

    def change_state(self, state):
        self.state = state
        self.setPixmap(self._pixmaps.get(state, self._pixmaps[ClientState.DROPPED]))

        if state == ClientState.ONLINE:
            self.setToolTip("Online")
        elif state == ClientState.RECONNECTING or state == ClientState.DROPPED:
            self.setToolTip("Reconnecting")
        else:
            self.setToolTip("Offline")
