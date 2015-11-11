from PyQt4.QtCore import pyqtSignal, Qt
from PyQt4.QtGui import QLabel, QMouseEvent, QAction, QMenu
import util
from client import ClientState


class StatusLogo(QLabel):
    disconnect_requested = pyqtSignal()
    reconnect_requested = pyqtSignal()

    def __init__(self, client, logo_file='window_icon.png'):
        QLabel.__init__(self)

        self.state = client.state
        self.setScaledContents(True)
        self.setMargin(3)

        self._pixmaps = {
            ClientState.ONLINE: util.pixmap('window_icon.png'),
            ClientState.RECONNECTING: util.pixmap('window_icon_yellow.png'),
            ClientState.DROPPED: util.pixmap('window_icon_red.png'),
            ClientState.NONE: util.pixmap('window_icon_red.png')
        }
        self.setMaximumSize(30, 30)

        client.state_changed.connect(self.change_state)
        self.change_state(client.state)

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        dc = QAction('Disconnect', None)
        rc = QAction('Reconnect', None)

        if self.state != ClientState.DISCONNECTED:
            menu.addAction(dc)
        if self.state != ClientState.ONLINE\
            and self.state != ClientState.RECONNECTING:
            menu.addAction(rc)

        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action == dc:
            self.disconnect_requested.emit()
        elif action == rc:
            self.reconnect_requested.emit()

    def change_state(self, state):
        self.state = state
        self.setPixmap(self._pixmaps.get(state, self._pixmaps[ClientState.DROPPED]))

        if state == ClientState.DROPPED:
            self.setToolTip("Offline")
        elif state == ClientState.RECONNECTING:
            self.setToolTip("Reconnecting")
        elif state == ClientState.ONLINE:
            self.setToolTip("Online")
