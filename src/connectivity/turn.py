import logging
from binascii import hexlify

import struct
from enum import Enum

from connectivity.stun import STUNMessage


class TURNState(Enum):
    INITIALIZING = 0
    BOUND = 1
    UNBOUND = 2
    STOPPED = 3


class TURNSession:
    """
    TURN session abstraction.

    Handles details of the TURN protocol.

    Currently event abstractions are implemented with three ugly callbacks:
      - send (Send raw bytes to the turn server)
      - recv (We received non-turn data on channel/address)
      - call_in (Schedule function to be called in x ms)

    This is done to keep the TURN specific code Qt-free.

    Of course; once we've got python3.5 and pyqt5/quamash on the client,
    these abstractions can be made much nicer.

    Until then.
    """
    def __init__(self, send, recv, call_in):
        self._pending_tx = {}
        self.logger = logging.getLogger(__name__)
        self.bindings = {}
        self.permissions = {}
        self._pending_bindings = []
        self.state = TURNState.INITIALIZING
        self.mapped_addr = (None, None)
        self.relayed_addr = (None, None)
        self.lifetime = 0
        self.write = send
        self.call_in = call_in
        self.recv = recv

    def start(self):
        self.logger.info("Requesting relay allocation")
        self.send(STUNMessage('Allocate',
                              [('REQUESTED-TRANSPORT', 17)]))
        self.call_in(self._retransmit, 15)

    def stop(self):
        self.state = TURNState.STOPPED

    def bind(self, channel_id, addr):
        self.permit(addr)
        self.logger.info("Requesting channel bind for {}:{}".format(channel_id, addr))
        channel = 0x4000+channel_id
        msg = STUNMessage('ChannelBind',
                          [('CHANNEL-NUMBER', channel),
                           ('XOR-PEER-ADDRESS', addr)])
        self.send(msg)
        self._pending_bindings.append((msg.transaction_id, addr, channel_id))

    def permit(self, addr):
        self.logger.info("Permitting sends from {}".format(addr))
        msg = STUNMessage('CreatePermission',
                          [('XOR-PEER-ADDRESS', addr)])
        self.send(msg)

    def send(self, stun_msg):
        self._pending_tx[stun_msg.transaction_id] = stun_msg
        self.write(stun_msg.to_bytes())

    _channeldata_format = struct.Struct('!HH')
    def send_to(self, addr, data):
        if isinstance(addr, int):
            msg = struct.pack('!HH', addr, len(data))
            self.write(msg + data)
        elif addr in self.bindings:
            header = TURNSession._channeldata_format.pack(self.bindings[addr], len(data))
            self.write(header+data)
        else:
            self.write(STUNMessage('Send',
                              [('XOR-PEER-ADDRESS', addr),
                               ('DATA', data)]).to_bytes())


    def _retransmit(self):
        if not self.state == TURNState.STOPPED:
            for tx, msg in self._pending_tx.items():
                self.logger.debug("Retransmitting {}".format(tx))
                self.write(msg)
            self.call_in(self._retransmit, 1)

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
            if not (sender_addr, sender_port) in self.permissions.keys():
                self.bind(1, (sender_addr, sender_port))
            self.recv((sender_addr, sender_port), data)
        if stun_msg.method_str == 'ChannelData':
            self.recv(attr['CHANNEL-NUMBER'], attr['DATA'])
        elif stun_msg.method_str == 'AllocateSuccess':
            self.logger.info("Relay allocated: {}".format(attr.get('XOR-RELAYED-ADDRESS')))
            self.handle_allocate_success(stun_msg)
        elif stun_msg.method_str == 'ChannelBindSuccess':
            for txid, (addr, port), channel_id in self._pending_bindings:
                if txid == stun_msg.transaction_id:
                    self.logger.info("Successfully bound {}:{} to {}".format(addr, port, channel_id))
                    self.bindings[addr] = channel_id
                    print(self.bindings)
                    self._pending_bindings.remove((txid, (addr,port), channel_id))
        elif stun_msg.method_str == 'CreatePermissionSuccess':
            pass
        elif stun_msg.method_str == 'RefreshSuccess':
            attr = dict(stun_msg.attributes)
            self.lifetime, = attr.get('LIFETIME')
            self.state = TURNState.BOUND
            self.schedule_refresh()
        if stun_msg.transaction_id in self._pending_tx.keys():
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
        self.call_in(self.refresh, 30)

    def refresh(self):
        self.write(STUNMessage('Refresh').to_bytes())

    def __str__(self):
        return "TURNSession({}, {}, {}, {})".format(self.state, self.mapped_addr, self.relayed_addr, self.lifetime)
