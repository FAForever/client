import config

from PyQt4.QtCore import QTimer, pyqtSignal
from PyQt4.QtNetwork import QUdpSocket, QHostAddress, QHostInfo

from connectivity.stun import STUNMessage
from connectivity.turn import TURNSession, TURNState
from decorators import with_logger


class QTurnSession(TURNSession):
    def __init__(self, turn_client):
        super(QTurnSession, self).__init__()
        self.turn_client = turn_client  # type: QTurnSocket

    def _call_in(self, func, timeout):
        self.turn_client.call_in(func, timeout)

    def _recvfrom(self, sender, data):
        self.turn_client.recvfrom(sender, data)

    def state_changed(self, new_state):
        self.turn_client.turn_state = new_state

    def channel_bound(self, address, channel):
        self.turn_client.channel_bound(address, channel)

    def _write(self, bytes):
        self.turn_client.send(bytes)

    def _recv(self, channel, data):
        self.turn_client.recv(channel, data)


@with_logger
class QTurnSocket(QUdpSocket):
    """
    Qt based TURN client, abstracts a normal socket
    and provides transparent TURN tunnelling functionality.
    """
    # Emitted when the TURN session changes state
    state_changed = pyqtSignal(TURNState)

    # Emitted when the TURN session is bound
    bound = pyqtSignal(tuple)

    @property
    def mapped_address(self):
        return self._session.mapped_addr

    @property
    def relay_address(self):
        return self._session.relayed_addr

    @property
    def turn_state(self):
        return self._state

    @turn_state.setter
    def turn_state(self, val):
        self._state = val
        self._logger.info("TURN state changed: {}".format(val))
        self.state_changed.emit(val)
        if val == TURNState.BOUND:
            self.bound.emit(self.relay_address)

    def __init__(self, port, data_cb):
        QUdpSocket.__init__(self)
        self._session = QTurnSession(self)
        self._state = TURNState.UNBOUND
        self.bindings = {}
        self.initial_port = port
        self._data_cb = data_cb
        self.turn_host, self.turn_port = config.Settings.get('turn/host', type=str, default='dev.faforever.com'), \
                               config.Settings.get('turn/port', type=int, default=3478)
        self._logger.info("Turn socket initialized: {}".format(self.turn_host))
        self.turn_address = None
        QHostInfo.lookupHost(self.turn_host, self._looked_up)
        self.bind(port)
        self.readyRead.connect(self._readyRead)
        self.error.connect(self._error)

    def randomize_port(self):
        self.abort()
        self.bind()

    def reset_port(self, to=None):
        self.abort()
        self.bind(to or self.initial_port)

    def _looked_up(self, info):
        self.turn_address = info.addresses()[0]

    def connect_to_relay(self):
        self._session.start()

    def stop(self):
        self.close()

    def permit(self, addr):
        self._session.permit(addr)

    def bind_address(self, addr):
        self._session.bind(addr)

    def channel_bound(self, addr, channel):
        (host, port) = addr
        self._logger.info("Bound channel {} to {}".format(channel, (host, port)))
        self.bindings[channel] = (host, int(port))

    def call_in(self, func, sec):
        timer = QTimer(self)
        timer.singleShot(sec * 1000, func)

    def _error(self):
        pass

    def recvfrom(self, sender, data):
        self._data_cb(sender, data)

    def recv(self, channel, data):
        self._logger.debug("{}/TURNData<<: {}".format(channel, data))
        try:
            self._data_cb(self.bindings[channel], data)
        except KeyError:
            self._logger.debug("No binding for channel: {}. Known: {}".format(channel, self.bindings))

    def send(self, data):
        """
        Write directly to the TURN relay
        :param data:
        :return:
        """
        self.writeDatagram(data, self.turn_address, self.turn_port)

    def sendto(self, data, address):
        if address in list(self.bindings.values()):
            self._logger.debug("Sending to {} through relay".format(address))
            self._session.send_to(data, address)
        else:
            host, port = address
            self._logger.debug("Sending to {} directly".format(address))
            self.writeDatagram(data, QHostAddress(host), port)

    def handle_data(self, addr, data):
        (host, port) = addr
        self._logger.debug("{}:{}/UDP<<".format(host, port))
        if self._session and self._session.is_stun_message(data):
            self._logger.debug("Handling using turn session")
            response = STUNMessage.from_bytes(data)
            self._session.handle_response(response)
        else:
            self._logger.debug("Emitting data, len: {}".format(len(data)))
            self._data_cb((host, port), data)

    def _readyRead(self):
        while self.hasPendingDatagrams():
            data, host, port = self.readDatagram(self.pendingDatagramSize())
            self.handle_data((host.toString(), int(port)), data)
