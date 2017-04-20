import logging
from abc import ABCMeta, abstractmethod

import struct
from enum import Enum

from connectivity.stun import STUNMessage, STUN_MAGIC_COOKIE


class TURNState(Enum):
    INITIALIZING = 0
    BOUND = 1
    UNBOUND = 2
    STOPPED = 3


class TURNSession(metaclass=ABCMeta):
    """
    Abstract TURN session abstraction.

    Handles details of the TURN protocol.
    """

    def __init__(self):
        self._pending_tx = {}
        self.logger = logging.getLogger(__name__)
        self.bindings = {}
        self._next_channel = 0x4000
        self.permissions = {}
        self._pending_bindings = []
        self._state = TURNState.INITIALIZING
        self.mapped_addr = (None, None)
        self.relayed_addr = (None, None)
        self.lifetime = 0

    @abstractmethod
    def _write(self, bytes):
        pass

    @abstractmethod
    def _call_in(self, timeout, func):
        pass

    @abstractmethod
    def _recv(self, channel, data):
        pass

    @abstractmethod
    def _recvfrom(self, sender, data):
        pass

    @abstractmethod
    def channel_bound(self, address, channel):
        pass

    @abstractmethod
    def state_changed(self, new_state):
        pass

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, val):
        if self._state != val:
            self._state = val
            self.state_changed(val)

    def start(self):
        self.logger.info("Requesting relay allocation")
        # Remove any previous allocation we may have
        self._write(STUNMessage('Refresh',
                               [('LIFETIME', 0)]).to_bytes())
        # Allocate a new UDP relay address
        self._send(STUNMessage('Allocate',
                               [('REQUESTED-TRANSPORT', 17)]))
        self._call_in(self._retransmit, 15)

    def stop(self):
        self.state = TURNState.STOPPED

    def is_stun_message(self, data):
        try:
            channel, len = struct.unpack('!HH', data[:4])
            if 0x4000 <= channel <= 0x7FFF:
                return True
            else:
                method, length, magic, tx_id = STUNMessage.parse_header(data[:20])
                return magic == STUN_MAGIC_COOKIE
        except:
            return False

    def bind(self, addr):
        if addr in self.bindings or addr in [addr for (_, addr, _)
                                             in self._pending_bindings]:
            return
        self.permit(addr)
        self.logger.info("Requesting channel bind for {}:{}".format(self._next_channel, addr))
        msg = STUNMessage('ChannelBind',
                          [('CHANNEL-NUMBER', self._next_channel),
                           ('XOR-PEER-ADDRESS', addr)])
        self._send(msg)
        self._pending_bindings.append((msg.transaction_id, addr, self._next_channel))
        self._next_channel += 1

    def permit(self, addr):
        self.logger.info("Permitting sends from {}".format(addr))
        msg = STUNMessage('CreatePermission',
                          [('XOR-PEER-ADDRESS', addr)])
        self._send(msg)

    def _send(self, stun_msg):
        self._pending_tx[stun_msg.transaction_id] = stun_msg
        self._write(stun_msg.to_bytes())

    _channeldata_format = struct.Struct('!HH')
    def send_to(self, data, addr):
        if isinstance(addr, int):
            msg = struct.pack('!HH', addr, len(data))
            self._write(msg + data)
        elif addr in self.bindings:
            header = TURNSession._channeldata_format.pack(self.bindings[addr], len(data))
            self._write(header + data)
        else:
            self._write(STUNMessage('Send',
                                    [('XOR-PEER-ADDRESS', addr),
                               ('DATA', data)]).to_bytes())

    def _retransmit(self):
        if not self.state == TURNState.STOPPED:
            for tx, msg in list(self._pending_tx.items()):
                self.logger.debug("Retransmitting {}".format(tx))
                # avoid retransmitting retransmissions
                self._write(msg.to_bytes())
            self._call_in(self._retransmit, 1)

    def handle_response(self, stun_msg):
        """
        Handle the given stun message, assumed to be a response from the server
        to a prior sent request

        :param stun_msg: STUNMessage
        """
        self.logger.debug("<<: {}".format(stun_msg))
        attr = dict(stun_msg.attributes)
        if stun_msg.method_str == 'DataIndication':
            self.logger.debug(stun_msg.attributes)
            data, (sender_addr, sender_port) = attr.get('DATA'), attr.get('XOR-PEER-ADDRESS')
            self.logger.debug("<<({}:{}): {}".format(sender_addr, sender_port, data))
            self._recvfrom((sender_addr, sender_port), data)
        if stun_msg.method_str == 'ChannelData':
            self._recv(attr['CHANNEL-NUMBER'], attr['DATA'])
        elif stun_msg.method_str == 'AllocateSuccess':
            self.logger.info("Relay allocated: {}".format(attr.get('XOR-RELAYED-ADDRESS')))
            self.handle_allocate_success(stun_msg)
        elif stun_msg.method_str == 'ChannelBindSuccess':
            for txid, (addr, port), channel_id in self._pending_bindings:
                if txid == stun_msg.transaction_id:
                    self.logger.info("Successfully bound {}:{} to {}".format(addr, port, channel_id))
                    self.bindings[(addr, port)] = channel_id
                    self.channel_bound((addr, port), channel_id)
                    self._pending_bindings.remove((txid, (addr,port), channel_id))
        elif stun_msg.method_str == 'CreatePermissionSuccess':
            pass
        elif stun_msg.method_str == 'RefreshSuccess':
            attr = dict(stun_msg.attributes)
            self.lifetime, = attr.get('LIFETIME')
            self.state = TURNState.BOUND
            self.schedule_refresh()
        if stun_msg.transaction_id in list(self._pending_tx.keys()):
            del self._pending_tx[stun_msg.transaction_id]

    def handle_allocate_success(self, stun_msg):
        attr = dict(stun_msg.attributes)
        self.mapped_addr = attr.get('XOR-MAPPED-ADDRESS')
        self.relayed_addr = attr.get('XOR-RELAYED-ADDRESS')
        self.lifetime, = attr.get('LIFETIME')
        self.state = TURNState.BOUND
        self.schedule_refresh()
        self.permit(self.mapped_addr)
        self.permit(('37.58.123.2', 6112))
        self.permit(('37.58.123.3', 6112))

    def schedule_refresh(self):
        self._call_in(self.refresh, 30)

    def refresh(self):
        self._write(STUNMessage('Refresh').to_bytes())
        for addr, channel in list(self.bindings.items()):
            self._write(STUNMessage('ChannelBind',
                  [('CHANNEL-NUMBER', channel),
                   ('XOR-PEER-ADDRESS', addr)]).to_bytes())

    def __str__(self):
        return "TURNSession({}, {}, {}, {})".format(self.state, self.mapped_addr, self.relayed_addr, self.lifetime)
