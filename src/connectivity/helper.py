from __future__ import division

from PyQt4.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt4.QtNetwork import QUdpSocket, QHostAddress
import time

from math import floor

from connectivity import QTurnClient
from connectivity.turn import TURNState
from decorators import with_logger


@with_logger
class RelayTest(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)

    def __init__(self, turn_client, socket):
        QObject.__init__(self)
        self._turnclient = turn_client
        self._socket = socket
        self.start_time, self.end_time = None, None
        self.addr = None
        self.received = set()
        self._sent, self._total = 0, 250
        self.host, self.port = None, None
        self._sendtimer = QTimer()
        self._sendtimer.timeout.connect(self.send)

    def start_relay_test(self, address):
        self.addr = address
        self._logger.info("Starting relay test")
        self._turnclient.received_indication_data.connect(self.receive)
        self._turnclient.permit(self.addr)

        self.start_time, self.end_time = time.time(), None
        host, port = self.addr
        self.host, self.port = QHostAddress(host), port

        self._sent = 0
        self.received = set()
        self._sendtimer.start(20)

        end_timer = QTimer()
        end_timer.singleShot(10000, self.end)

    @property
    def report(self):
        return "Relay address: {}\nReceived {} packets in {}s. {}% loss.". \
                    format("{}:{}".format(*self.addr),
                           len(self.received),
                           round((time.time()-self.start_time), 2),
                           round(100-(len(self.received)/self._sent) * 100), 2)

    def send(self):
        self._socket.writeDatagram(('{}'.format(self._sent)).encode(), self.host, self.port)
        if self._sent >= self._total:
            self._sendtimer.stop()
        self._sent += 1

    def end(self):
        if self.end_time:
            return
        self.end_time = time.time()
        self._sendtimer.stop()
        self._logger.info('Relay test finished')
        self.finished.emit()
        self._turnclient.received_indication_data.disconnect(self.receive)

    def receive(self, sender, data):
        self.received.add(int(data.decode()))
        self.progress.emit(self.report)
        if len(self.received) == self._total:
            self.end()


@with_logger
class ConnectivityHelper(QObject):
    connectivity_status_established = pyqtSignal(str, str)
    relay_bound = pyqtSignal()

    relay_test_finished = pyqtSignal()
    relay_test_progress = pyqtSignal(str)

    error = pyqtSignal(str)

    def __init__(self, client, port):
        QObject.__init__(self)
        self._client = client
        self._port = port
        self._socket = QUdpSocket()
        self._socket.readyRead.connect(self._socket_readyread)
        self._turnclient = QTurnClient()
        self._turnclient.state_changed.connect(self.turn_state_changed)
        self._turnclient.received_indication_data.connect(self._on_indication)
        self._client.subscribe_to('connectivity', self)
        self._socket.bind(self._port)
        self.relay_address, self.mapped_address = None, None
        self._relay_test = None
        self.state = None
        self.addr = None

    def start_test(self):
        self.send('InitiateTest', [self._port])

    def start_relay_test(self):
        if not self._relay_test:
            self._relay_test = RelayTest(self._turnclient, self._socket)
            self._relay_test.finished.connect(self.relay_test_finished.emit)
            self._relay_test.progress.connect(self.relay_test_progress.emit)

        if not self._turnclient.state == TURNState.BOUND:
            self._turnclient.run()
            self._turnclient.bound.connect(self._relay_test.start_relay_test, Qt.UniqueConnection)

            def _cleanup():
                try:
                    self._turnclient.bound.disconnect(self._relay_test.start_relay_test)
                except TypeError:
                    # For some reason pyqt raises _TypeError_ here
                    pass

            self._relay_test.finished.connect(_cleanup, Qt.UniqueConnection)
        else:
            self._relay_test.start_relay_test(self.mapped_address)

    def turn_state_changed(self, state):
        if state == TURNState.BOUND:
            self.relay_address = self._turnclient.relay_address
            self.mapped_address = self._turnclient.relay_address
            self.relay_bound.emit()

    def handle_SendNatPacket(self, msg):
        target, message = msg['args']
        host, port = target.split(':')
        self._socket.writeDatagram(b'\x08'+message.encode(), QHostAddress(host), int(port))

    def handle_ConnectivityState(self, msg):
        state, addr = msg['args']
        host, port = addr.split(':')
        self.state, self.mapped_address = state, (host, port)
        self.connectivity_status_established.emit(self.state, self.addr)
        self._logger.info("Connectivity state is {}, mapped address: {}".format(state, addr))

    def handle_message(self, msg):
        command = msg.get('command')
        if command == 'CreatePermission':
            self._turnclient.permit(msg['args'])

    def send(self, command, args):
        self._client.send({
            'command': command,
            'target': 'connectivity',
            'args': args or []
        })

    def prepare(self):
        if self.state == 'STUN' and not self._turnclient.state == TURNState.BOUND:
            self._turnclient.run()
        else:
            self.relay_bound.emit()

    def send_udp(self, bytes, addr):
        host, port = addr
        self._socket.writeDatagram(bytes, QHostAddress(host), int(port))

    def _on_indication(self, addr, data):
        message = data.decode()

    def _socket_readyread(self):
        while self._socket.hasPendingDatagrams():
            data, host, port = self._socket.readDatagram(self._socket.pendingDatagramSize())
            self.send('ProcessNatPacket',
                      ["{}:{}".format(host.toString(), port), data.encode()])
