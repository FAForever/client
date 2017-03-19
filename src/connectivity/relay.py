from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtNetwork import QUdpSocket, QHostAddress

from decorators import with_logger


@with_logger
class Relay(QObject):
    bound = pyqtSignal(int)

    def __init__(self, game_port, login, peer_id, recv):
        QObject.__init__(self)
        self._logger.info("Allocating local relay for {}, {}".format(login, peer_id))
        self._socket = QUdpSocket()
        self._socket.stateChanged.connect(self._state_changed)
        self._socket.readyRead.connect(self._ready_read)
        self.game_port = game_port
        self.login, self.peer_id = login, peer_id
        self.recv = recv

    def listen(self):
        self._socket.bind()

    def send(self, message):
        self._logger.debug("game at 127.0.0.1:{}<<{} len: {}".format(self.game_port, self.peer_id, len(message)))
        self._socket.writeDatagram(message, QHostAddress.LocalHost, self.game_port)

    def _state_changed(self, state):
        if state == QUdpSocket.BoundState:
            self.bound.emit(self._socket.localPort())

    def _ready_read(self):
        while self._socket.hasPendingDatagrams():
            data, host, port = self._socket.readDatagram(self._socket.pendingDatagramSize())
            self._logger.debug("{}>>{}/{}".format(self._socket.localPort(), self.login, self.peer_id))
            self.recv(data)
