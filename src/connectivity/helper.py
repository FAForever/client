from __future__ import division

from functools import partial

from PyQt4.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer, QMetaObject, Q_ARG, Qt
from PyQt4.QtNetwork import QUdpSocket, QHostAddress, QAbstractSocket
import time

from connectivity import QTurnSocket
from connectivity.relay import Relay
from connectivity.turn import TURNState
from decorators import with_logger


from PyQt4 import QtGui, uic


@with_logger
class RelayTest(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)

    def __init__(self, socket):
        QObject.__init__(self)
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
        self._socket.data.connect(self.receive)
        self._socket.permit(self.addr)

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
        self.socket.data.disconnect(self.receive)

    def receive(self, sender, data):
        self.received.add(int(data.decode()))
        self.progress.emit(self.report)
        if len(self.received) == self._total:
            self.end()


@with_logger
class ConnectivityHelper(QObject):
    connectivity_status_established = pyqtSignal(str, object)

    # Emitted when a peer is bound to a local port
    peer_bound = pyqtSignal(str, int, int)

    ready = pyqtSignal()
    start_test = pyqtSignal()
    relay_test_finished = pyqtSignal()
    relay_test_progress = pyqtSignal(str)

    command_msg = pyqtSignal(dict)

    error = pyqtSignal(str)

    def __init__(self, client, port):
        QObject.__init__(self)
        self._client = client
        self._port = port
        self.game_port = port+1
        self.relay_address, self.mapped_address = None, None
        self._relay_test = None
        self._relays = {}
        self.state = None
        self.addr = None
        self.start_test.connect(self.run_test)
        self.command_msg.connect(self.handle_cmd_message)

    @property
    def is_ready(self):
        return (self.relay_address is not None
                and self.relay_address is not [None, None]
                and self.mapped_address is not None
                and self._socket.state() == QAbstractSocket.BoundState)

    @pyqtSlot()
    def run_test(self):
        self._client.subscribe_to('connectivity', self)
        self._socket = QTurnSocket(self._port, self._on_data)
        self._socket.state_changed.connect(self.turn_state_changed)

        self.send('InitiateTest', [self._port])

    def start_relay_test(self):
        if not self._relay_test:
            self._relay_test = RelayTest(self._socket)
            self._relay_test.finished.connect(self.relay_test_finished.emit)
            self._relay_test.progress.connect(self.relay_test_progress.emit)

        if not self._socket.turn_state == TURNState.BOUND:
            self._socket.connect_to_relay()
            self._socket.bound.connect(self._relay_test.start_relay_test, Qt.UniqueConnection)

            def _cleanup():
                try:
                    self._socket.bound.disconnect(self._relay_test.start_relay_test)
                except TypeError:
                    # For some reason pyqt raises _TypeError_ here
                    pass

            self._relay_test.finished.connect(_cleanup, Qt.UniqueConnection)
        else:
            self._relay_test.start_relay_test(self.mapped_address)

    def turn_state_changed(self, state):
        if state == TURNState.BOUND:
            self.relay_address = self._socket.relay_address
            self.mapped_address = self._socket.relay_address
            self.ready.emit()

    def handle_SendNatPacket(self, msg):
        target, message = msg['args']
        host, port = target.split(':')
        if self.state is None and self._socket.localPort() == self._port:
            self._socket.randomize_port()
        self._socket.writeDatagram(b'\x08'+message.encode(), QHostAddress(host), int(port))

    def handle_ConnectivityState(self, msg):
        from client import ClientState
        state, addr = msg['args']
        if state == 'BLOCKED':
            self._logger.warning("Outbound traffic is blocked")
            QtGui.QMessageBox.warning(None, "Traffic Blocked", "Your outbound traffic appears to be blocked. Try restarting FAF. <br/> If the error persists please contact a moderator and send your logs. <br/> We are already working on a solution to this problem.")
            self._client.state = ClientState.NONE
        else:
            host, port = addr.split(':')
            self.state, self.mapped_address = state, (host, port)
            self._logger.info("Connectivity state is {}, mapped address: {}".format(state, addr))
            self.connectivity_status_established.emit(self.state, addr)

    def handle_CreatePermission(self, msg):
        self._socket.permit(msg['args'])

    @pyqtSlot(dict)
    def handle_cmd_message(self, msg):
        command = msg.get('command')
        f = getattr(self, "handle_" + command)

        if not f:
            logger.warn("No receiver for message {}".format(message))
            return

        f(msg)

    def bind(self, (host, port), login, peer_id):
        host, port = host, int(port)
        relay = Relay(self.game_port, login, peer_id, partial(self.send_udp, (host, port)))
        relay.bound.connect(partial(self.peer_bound.emit, login, peer_id))
        relay.listen()
        self._relays[(host, port)] = relay

    def send(self, command, args):
        meta = self._client.metaObject()
        data = {
            'command': command,
            'target': 'connectivity',
            'args': args or []
        }

        meta.invokeMethod(self._client, "send", Qt.QueuedConnection, Q_ARG(dict, data))

    @pyqtSlot(dict)
    def handle_game_message(self, message):
        command, args = message.get('command'), message.get('args', [])

        if command == 'SendNatPacket':
            addr_and_port, message = args
            host, port = addr_and_port.split(':')
            self.send(message, (host, port))
        elif command == 'CreatePermission':
            addr_and_port = args[0]
            host, port = addr_and_port.split(':')
            self.permit((host, port))
        elif command == 'JoinGame':
            addr, login, peer_id = args
            self.bind(addr, login, peer_id)
        elif command == 'ConnectToPeer':
            addr, login, peer_id = args
            self.bind(addr, login, peer_id)

    @pyqtSlot()
    def prepare(self):
        if self.state == 'STUN' and not self._socket.turn_state == TURNState.BOUND:
            self._socket.connect_to_relay()
        elif self.state == 'BLOCKED':
            pass
        else:
            self.ready.emit()

    def send_udp(self, (host, port), data):
        host, port = host, int(port)
        self._socket.sendto(data, (host, port))

    def _on_data(self, addr, data):
        host, port = addr
        if not self._process_natpacket(data, addr):
            try:
                relay = self._relays[(host, int(port))]
                self._logger.debug('{}<<{} len: {}'.format(relay.peer_id, addr, len(data)))
                relay.send(data)
            except KeyError:
                self._logger.debug("No relay for data from {}:{}".format(host, port))

    def _process_natpacket(self, data, addr):
        """
        Process data from given address as a natpacket

        Returns true iff it was processed as such
        :param data:
        :param addr:
        :return:
        """
        try:
            if data.startswith(b'\x08'):
                host, port = addr
                msg = data[1:].decode()
                self.send('ProcessNatPacket',
                          ["{}:{}".format(host, port), msg])
                if msg.startswith('Bind'):
                    peer_id = int(msg[4:])
                    if (host, port) not in self._socket.bindings:
                        self._logger.info("Binding {} to {}".format((host, port), peer_id))
                        self._socket.bind_address((host, port))
                    self._logger.info("Processed bind request")
                else:
                    self._logger.info("Unknown natpacket")
                return True
        except UnicodeDecodeError:
            return
