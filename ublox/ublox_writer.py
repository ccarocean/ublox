import struct


class UBXWriter:
    def __init__(self, dev, msg_dict):
        self._dev = dev
        self._sync1 = b'\xb5'
        self._sync2 = b'\x62'
        self._count = 0
        self._msg_dict = msg_dict

    def write_packet(self, payload, msgid):
        buff = struct.pack(b'H', msgid) + struct.pack(b'<H', len(payload)) + payload
        ck_a, ck_b = self.checksum(buff)
        full_packet = self._sync1 + self._sync2 + buff + struct.pack('BB', ck_a, ck_b)
        self._dev.write(full_packet)

    def checksum(self, buff):
        a, b = 0, 0
        for i in buff:
            a += i
            b += a
        a = a & 0xff
        b = b & 0xff
        return a, b
