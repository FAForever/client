import logging
from binascii import hexlify

import config

from PyQt4.QtCore import QObject, QTimer, pyqtSignal
from PyQt4.QtNetwork import QUdpSocket

from connectivity.stun import STUNMessage
from connectivity.turn import TURNSession, TURNState


class QTurnSession(TURNSession):
    def __init__(self, turn_client):
        super(QTurnSession, self).__init__()
        self.turn_client = turn_client  # type: QTurnClient

    def _call_in(self, func, timeout):
        self.turn_client.call_in(func, timeout)

    def _recvfrom(self, sender, data):
        self.turn_client.recvfrom(sender, data)

    def state_changed(self, new_state):
        self.turn_client.state_changed.emit(new_state)

    def _write(self, bytes):
        self.turn_client.send(bytes)

    def _recv(self, channel, data):
        self.turn_client.recv(channel, data)


class QTurnClient(QObject):
    """
    Qt based TURN client
    """
    # Emitted when we receive data on a given port
    received_data = pyqtSignal(int, str)

    # Emitted when the TURN session changes state
    state_changed = pyqtSignal(TURNState)

    def __init__(self):
        QObject.__init__(self)
        self.logger = logging.getLogger(__name__)
        self._socket = QUdpSocket()
        self._session = QTurnSession(self)

        self._socket.connected.connect(self._session.start)
        self._socket.readyRead.connect(self._socket_readyRead)
        self._socket.error.connect(self._error)

    def run(self):
        self._socket.connectToHost(config.Settings.get('turn/host', type=str, default='dev.faforever.com'),
                                   config.Settings.get('turn/port', type=int, default=3478))

    @property
    def mapped_address(self):
        return self._session.mapped_addr

    @property
    def relay_address(self):
        return self._session.relayed_addr

    def call_in(self, func, sec):
        timer = QTimer(self)
        timer.singleShot(sec * 1000, func)

    def _error(self):
        pass

    def recvfrom(self, sender, data):
        self.logger.debug("Received non channel data {} from {}".format(hexlify(data), sender))

    def recv(self, channel, data):
        self.logger.debug("Received {} on {}".format(hexlify(data), channel))
        self.received_data.emit(channel, data)

    def send(self, data):
        """
        Write directly to the underlying socket

        Overrides TURNSession._send
        :param data:
        :return:
        """
        self._socket.write(data)

    def _socket_readyRead(self):
        while self._socket.hasPendingDatagrams():
            data, host, port = self._socket.readDatagram(self._socket.pendingDatagramSize())
            response = STUNMessage.from_bytes(data)
            self._session.handle_response(response)
