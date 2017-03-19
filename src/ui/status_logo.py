from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QLabel, QAction, QMenu
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

        normal, yellow, red = list(map(util.pixmap, [
            'window_icon.png',
            'window_icon_yellow.png',
            'window_icon_red.png'
        ]))

        self._pixmaps = {
            ClientState.SHUTDOWN: red,
            ClientState.NONE: red,
            ClientState.DISCONNECTED: red,
            ClientState.CONNECTING: yellow,
            ClientState.CONNECTED: normal,
            ClientState.LOGGED_IN: normal,
        }
        self._tooltips = {
            ClientState.SHUTDOWN: "Shutting down",
            ClientState.NONE: "Unknown",
            ClientState.DISCONNECTED: "Disconnected",
            ClientState.CONNECTING: "Connecting",
            ClientState.CONNECTED: "Connected",
            ClientState.LOGGED_IN: "Logged in",
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
        if self.state not in [
                ClientState.CONNECTING,
                ClientState.CONNECTED,
                ClientState.LOGGED_IN]:
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
        self.setPixmap(self._pixmaps[state])
        self.setToolTip(self._tooltips[state])
