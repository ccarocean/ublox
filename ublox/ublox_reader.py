import struct
from .messages import UnknownPacket


class UBXReader:
    """ Class for reading packet from GPS. """
    def __init__(self, dev, msg_dict):
        self._dev = dev  #Device
        self._sync1 = b'\xb5'  # First synchronization byte
        self._sync2 = b'\x62'  # Second synchronization byte
        self._msg_dict = msg_dict

    def read_packet(self):
        """ Public read packet function. """
        msg_id, payload = self._read_packet()
        try:
            return self._msg_dict[msg_id](payload)
        except KeyError:
            return UnknownPacket(msg_id, payload)

    def _read_packet(self):
        """ Private read packet function. """
        count = 0   # This is used to read more bits incremented by one each time the sync bits are found but the check
                    # sums do not work properly. This will fix an infinite loop in the rare case that the sync bits are
                    # found an even number of bits away from each other but not on purpose.
        cs = False
        while not cs:  # While checksums aren't working
            self._dev.read(count)  # Read from device
            last_byte = self._dev.read(1)
            curr_byte = self._dev.read(1)
            while last_byte != self._sync1 or curr_byte != self._sync2:
                last_byte = curr_byte
                curr_byte = self._dev.read(1)
            buff = self._dev.read(4)
            msg_id, length = struct.unpack('<HH', buff)
            payload = self._dev.read(length)
            ck_a, ck_b = struct.unpack('BB', self._dev.read(2))
            cs = self.checksum(ck_a, ck_b, buff+payload)
            count += 1
        return msg_id, payload

    def checksum(self, ck_a, ck_b, buff):
        """ Check the checksum to make sure packet coming in contains correct data. """
        a, b = 0, 0
        for i in buff:
            a += i
            b += a
        a = a & 0xff
        b = b & 0xff
        if a != ck_a or b != ck_b:
            return False
        else:
            return True
