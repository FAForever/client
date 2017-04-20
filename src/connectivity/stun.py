import binascii
import random
import struct
import ipaddress

STUN_MAGIC_COOKIE = 0x2112A442
STUN_METHODS = {
    "Binding": 0x001,
    "BindingSuccess": 0x101,
    "Allocate": 0x003,
    "AllocateSuccess": 0x103,
    "Refresh": 0x004,
    "RefreshSuccess": 0x104,
    "RefreshError": 0x114,
    "Send": 0x006,
    "SendError": 0x116,
    "Data": 0x007,
    "DataIndication": 0x017,
    "CreatePermission": 0x008,
    "CreatePermissionSuccess": 0x108,
    "ChannelBind": 0x009,
    "ChannelBindSuccess": 0x109,
    "ChannelData": 0x999,
}
STUN_METHOD_VALUES = {v: k for k, v in list(STUN_METHODS.items())}
STUN_ATTRIBUTES = {
    'MAPPED-ADDRESS': 0x0001,
    'CHANNEL-NUMBER': 0x000c,
    'LIFETIME': 0x000d,
    'Reserved (was BANDWIDTH)': 0x0010,
    'XOR-PEER-ADDRESS': 0x0012,
    'DATA': 0x0013,
    'XOR-RELAYED-ADDRESS': 0x0016,
    'EVEN-PORT': 0x0018,
    'REQUESTED-TRANSPORT': 0x0019,
    'XOR-MAPPED-ADDRESS': 0x0020,
    'DONT-FRAGMENT': 0x001a,
    'Reserved (was TIMER-VAL)': 0x0021,
    'RESERVATION-TOKEN': 0x0022,
    'RESPONSE-ORIGIN': 0x802b,
    'SOFTWARE': 0x8022
}
STUN_ATTRIBUTE_VALUES = {v: k for k, v in list(STUN_ATTRIBUTES.items())}


class STUNAttribute:
    # Type, Value
    _header_format = struct.Struct('!HH')
    # family, port, addr
    _address_header = struct.Struct('!xBH')

    def __init__(self, type=None, val=None, buffer=None):
        self.body = buffer or None
        if self.body:
            self.type, _, self.val = STUNAttribute.decode(self.body)
        else:
            self.body = STUNAttribute.encode(type, val)
            self.type = type
            self.val = val

    @staticmethod
    def decode_address(buffer, xor=False):
        family, port = STUNAttribute._address_header.unpack_from(buffer)
        if family != 0x01:
            raise ValueError("IPv6 not supported")
        addr, = struct.unpack_from('!I', buffer, 4)
        if xor:
            addr ^= STUN_MAGIC_COOKIE
            port ^= (STUN_MAGIC_COOKIE & 0xFFFF0000) >> 16
        return str(ipaddress.IPv4Address(addr)), port

    @staticmethod
    def decode(buffer):
        header_sz = 4
        type, value_length = STUNAttribute._header_format.unpack_from(buffer[:header_sz])
        type_str = STUN_ATTRIBUTE_VALUES.get(type)
        padding = 4-(value_length % 4)  # align to 32-bit boundaries
        if padding == 4:
            padding = 0
        total_length = header_sz + padding + value_length
        val = ''
        if type_str in ('XOR-MAPPED-ADDRESS',
                        'XOR-RELAYED-ADDRESS',
                        'XOR-PEER-ADDRESS',
                        'MAPPED-ADDRESS',
                        'RESPONSE-ORIGIN'):
            val = STUNAttribute.decode_address(buffer[header_sz:], xor='XOR' in type_str)
        elif type_str == 'LIFETIME':
            val = struct.unpack_from('!I', buffer[header_sz:])
        elif type_str == 'DATA':
            val = buffer[header_sz:header_sz+value_length]
        return type_str, total_length, val

    @staticmethod
    def encode(type, val):
        """
        STUN attributes are 'TLV'-encoded

        :param type: The STUN attribute type to encode
        :param val: The value to encode
        :return: packed binary sequence
        """
        type_val = STUN_ATTRIBUTES.get(type)
        if type == 'DATA':
            hd = struct.pack('!HH', type_val, len(val))
            return hd + val
        elif type == "REQUESTED-TRANSPORT":
            return struct.pack('!HHB3x', type_val, 4, val)
        elif type == "LIFETIME":
            return struct.pack('!HHI', type_val, 4, val)
        elif type == "CHANNEL-NUMBER":
            return struct.pack('!HHHxx', type_val, 4, val)
        elif type == "XOR-PEER-ADDRESS":
            addr, port = val
            addr = int(ipaddress.IPv4Address(str(addr)))
            port ^= (STUN_MAGIC_COOKIE & 0xFFFF0000) >> 16
            addr ^= STUN_MAGIC_COOKIE
            return struct.pack('!HHxBHI', type_val, 8, 0x1, port, addr)
        else:
            length = len(val)
            return struct.pack('!HH%ip' % length, type, length, val)


class STUNMessage:
    _header_format = struct.Struct('!HHl12s')

    def __init__(self, method=None, attributes=None, transaction_id=None, body=None, header=None):
        if isinstance(method, str):
            self.method = STUN_METHODS[method]
        elif isinstance(method, int):
            self.method = method
        else:
            raise ValueError("Method must be str or int from STUN_METHODS")

        self.attributes = attributes or []

        self.transaction_id = transaction_id or self._make_transaction_id()
        self.body = body or self._make_body()
        self.header = header or self._make_header()

    @property
    def method_str(self):
        return STUN_METHOD_VALUES.get(self.method)

    def _make_header(self):
        buf = bytearray(20)
        self._header_format.pack_into(buf,
                                      0,
                                      self.method,
                                      len(self.body),
                                      STUN_MAGIC_COOKIE,
                                      self.transaction_id)
        return buf

    def _make_body(self):
        return b''.join([STUNAttribute.encode(*t) for t in self.attributes])

    @staticmethod
    def _make_transaction_id():
        a = ''.join([random.choice('0123456789ABCDEF') for x in range(24)])
        return binascii.a2b_hex(a)

    @staticmethod
    def parse_header(data):
        """
        Parse the binary stun header

        :param data: buffer to parse, must be of length 20
        :return: method, length, magic token, tx_id
        """
        return STUNMessage._header_format.unpack_from(data)

    @staticmethod
    def parse_body(data):
        """
        Parse the binary stun body

        :param data: buffer to parse, must not contain stun header
        :return: list of key-value tuples
        """
        pos = 0
        attrs = []
        while pos < len(data):
            type, eaten, value = STUNAttribute.decode(data[pos:])
            pos += eaten
            attrs.append((type, value))
        return attrs

    @staticmethod
    def from_bytes(buffer):
        channel, len = struct.unpack('!HH', buffer[:4])
        if 0x4000 <= channel <= 0x7FFF:
            return STUNMessage('ChannelData',
                               [('CHANNEL-NUMBER', channel),
                                ('DATA', buffer[4:4+len])])

        header = buffer[:20]
        method, length, magic, tx_id = STUNMessage.parse_header(header)
        if length:
            body = buffer[20:length]
            attributes = STUNMessage.parse_body(body)
        else:
            body = b''
            attributes = []
        return STUNMessage(method=method, attributes=attributes, transaction_id=tx_id, body=body, header=header)

    def to_bytes(self):
        return self.header + self.body

    def __str__(self):
        return "STUNMessage({}, {}, {})".format(STUN_METHOD_VALUES.get(self.method),
                                                binascii.hexlify(self.transaction_id),
                                                len(self.body))
