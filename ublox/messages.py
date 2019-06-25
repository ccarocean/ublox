from abc import ABC, abstractmethod
import struct
from dataclasses import dataclass
import datetime as dt
from collections import defaultdict


# Table of implemented packets that can be sent and received
_LOOKUPTABLE = {
    'CFG-INFMSG-UBX_USB':                (0x20920004, 'B'),
    'CFG-INFMSG-UBX_UART1':              (0x20920002, 'B'),
    'CFG-MSGOUT-UBX_NAV_HPPOSLLH_USB':   (0x20910036, 'B'),
    'CFG-MSGOUT-UBX_NAV_HPPOSLLH_UART1': (0x20910034, 'B'),
    'CFG-MSGOUT-UBX_NAV_TIMEUTC_UART1':  (0x2091005c, 'B'),
    'CFG-MSGOUT-UBX_NAV_TIMEUTC_USB':    (0x2091005e, 'B'),
    'CFG-MSGOUT-UBX_RXM_RAWX_UART1':     (0x209102a5, 'B'),
    'CFG-MSGOUT-UBX_RXM_RAWX_USB':       (0x209102a7, 'B'),
    'CFG-RATE-MEAS':                     (0x30210001, 'H'),
    'CFG-SIGNAL-BDS_B2_ENA':             (0x1031000e, 'B'),
    'CFG-UART1-BAUDRATE':                (0x40520001, 'L'),
    'CFG-UART1INPROT-NMEA':              (0x10730002, 'B'),
    'CFG-UART1INPROT-RTCM3X':            (0x10730004, 'B'),
    'CFG-UART2-ENABLED':                 (0x10530005, 'B'),
    'CFG-USBINPROT-NMEA':                (0x10770002, 'B'),
    'CFG-USBINPROT-RTCM3X':              (0x10770004, 'B'),
    'CFG-USBOUTPROT-NMEA':               (0x10780002, 'B'),
    'CFG-USBOUTPROT-RTCM3X':             (0x10780004, 'B'),
    'CFG-USB-ENABLED':                   (0x10650001, 'B'),
    'CFG-UART1-ENABLED':                 (0x10520005, 'B'),
    'CFG-TXREADY-ENABLED':               (0x10a20001, 'B')
}


# Lookup table for GPS codes
_LOOKUP_GPS = {0: 'G', 1: 'S', 2: 'E', 3: 'C', 6: 'R'}


def str2type(type, string):
    """ Takes in string and type and returns desired value. """
    if type in {'B', 'b', 'H', 'h', 'l', 'L'}:
        return int(string, 0)
    elif type in {'f', 'd'}:
        return float(string)
    raise ValueError('Type is not in accepted types. ')


def x2bool(num, val):
    """ Takes in a number of bits and binary value and returns desired bools. """
    return tuple((val & 2**i) != 0 for i in range(num-1, -1, -1))


class Packet(ABC):
    """ Basic packet for inheritance. """
    id = 0x0000
    longname = 'Unknown Packet'


class ReceivedPacket(Packet, ABC):
    """ Received packet for inheritance. """
    pass


class SendPacket(Packet, ABC):
    """ Send packet for inheritance. """
    @abstractmethod
    def payload(self) -> bytes:
        pass


class UnknownPacket(ReceivedPacket):
    """ Class to represent a received packet that is not implemented in our software. """
    longname = "Unknown packet"

    def __init__(self, id, payload):
        self._id = id
        self._payload = payload

    def __str__(self):
        print('Unknown Packet. ID: ' + str(self._id))

    @property
    def msg_id(self):
        return self._id

    @property
    def payload(self):
        return self._payload


class AckAck(ReceivedPacket):
    """ Packet to show acknowledgement of reception of packet by GPS. """
    id = 0x0150
    longname = "Message acknowledged from GPS"

    def __init__(self, payload):
        self._clsID, self._msgID = struct.unpack('<BB', payload)

    @property
    def clsID(self):
        return self._clsID

    @property
    def msgID(self):
        return self._msgID


class AckNak(ReceivedPacket):
    """ Packet to show GPS did not acknowledge a packet it received. """
    id = 0x0005
    longname = "Message not acknowledged from GPS"

    def __init__(self, payload):
        self._clsID, self._msgID = struct.unpack('<BB', payload)

    @property
    def clsID(self):
        return self._clsID

    @property
    def msgID(self):
        return self._msgID


class CfgValgetSend(SendPacket):
    """ Send Packet to get current configuration values. """
    id = 0x8B06
    longname = 'Get current configuration values'

    def __init__(self, values, layer='default'):
        self._values = values
        layerlookup = {'ram': b'\x00', 'bbr': b'\x01', 'flash': b'\x02', 'default': b'\x07'}
        try:
            self._layer = layerlookup[layer.lower()]
        except KeyError:
            raise ValueError(f"'{layer}' is not a valid layer, must be 'ram', 'bbr', or 'flash'")

    def payload(self) -> bytes:
        payload_ = [b'\x00' + self._layer + b'\x00\x00']
        for name, value in self._values:
            key, type_ = _LOOKUPTABLE[name.upper()]
            payload_.append(struct.pack('<L'+type_, key, str2type(type_, value)))

        return b''.join(payload_)


class CfgValsetSend(SendPacket):
    """ Send Packet to set configuration values. """
    id = 0x8A06
    longname = 'Set configuration values'

    def __init__(self, config):
        self._config = config

    def payload(self) -> bytes:
        payload_ = [b'\x00\x01\x00\x00']
        for name, value in self._config.items():
            key, type_ = _LOOKUPTABLE[name.upper()]
            payload_.append(struct.pack('<L'+type_, key, str2type(type_, value)))

        return b''.join(payload_)


class CfgValgetRec(ReceivedPacket):
    """ Receive packet to get current configuration values. """
    id = 0x8B06
    longname = 'Received current configuration values'

    def __init__(self, payload):
        l = len(payload)
        self._version, self._layer, _, _ = struct.unpack('<BBBB', payload[0:4])
        num = len(payload) - 4
        self._keyvals = []
        for i in range(num):
            self._keyvals.append(struct.unpack('B', payload[i+5]))

    @property
    def version(self):
        return self._version

    @property
    def layer(self):
        return self._layer

    @property
    def keyvals(self):
        return self._keyvals


class InfDebug(ReceivedPacket):
    """ Receive debugging message. """
    id = 0x0404
    longname = 'Debugging message'

    def __init__(self, payload):
        self._message = payload.decode('ascii')

    @property
    def message(self):
        return self._message


class InfError(ReceivedPacket):
    """ Receive error message. """
    id = 0x0004
    longname = 'Error message'

    def __init__(self, payload):
        self._message = payload.decode('ascii')

    @property
    def message(self):
        return self._message


class InfNotice(ReceivedPacket):
    """ Receive notice message. """
    id = 0x0204
    longname = 'Notice message'

    def __init__(self, payload):
        self._message = payload.decode('ascii')

    @property
    def message(self):
        return self._message


class InfTest(ReceivedPacket):
    """ Receive testing message. """
    id = 0x0304
    longname = 'Testing message'

    def __init__(self, payload):
        self._message = payload.decode('ascii')

    @property
    def message(self):
        return self._message


class InfWarning(ReceivedPacket):
    """ Receive warning message. """
    id = 0x0104
    longname = 'Warning message'

    def __init__(self, payload):
        self._message = payload.decode('ascii')

    @property
    def message(self):
        return self._message


class NavHPPOSLLH(ReceivedPacket):
    """ Receive packet with high precision godetic positon solution from GPS. """
    id = 0x1401
    longname = 'High precision geodetic position solution'

    def __init__(self, payload):
        _, _, _, _, self._iTOW, lon_tmp, lat_tmp, height_tmp, hMSL_tmp, lon_hp, lat_hp, height_hp, hMSL_hp, hAcc_tmp, \
        vAcc_tmp = struct.unpack('<BBBBLllllbbbbLL', payload)
        self._lon = 10**-7 * (lon_tmp + lon_hp * 10**-2)  # degrees
        self._lat = 10**-7 * (lat_tmp + lat_hp * 10**-2)  # degrees
        self._height = (height_tmp + 0.1*height_hp) / 1000  # meters above ellipsoid
        self._hMSL = (hMSL_tmp + 0.1*hMSL_hp) / 1000  # meters above mean sea level
        self._vAcc = (vAcc_tmp * 0.1) / 1000  # meters horizontal accuracy estimate
        self._hAcc = (hAcc_tmp * 0.1) / 1000  # meters - vertical accuracy estimate

    def __str__(self):
        return f'Received Packet:    {self.longname}, ID: {self.id}\n' \
               f'Latitude:           {self.lat}±{self.hAcc}\n' \
               f'Longitude:          {self.lon}±{self.hAcc}\n' \
               f'Height above Geoid: {self.height}±{self.vAcc}\n' \
               f'Height aove MSL:    {self.hMSL}±{self.vAcc}\n' \
               f'iTOW (millisecond time of week): {self.iTOW}\n'

    @property
    def iTOW(self):
        return self._iTOW

    @property
    def lon(self):
        return self._lon

    @property
    def lat(self):
        return self._lat

    @property
    def height(self):
        return self._height

    @property
    def hMSL(self):
        return self._hMSL

    @property
    def vAcc(self):
        return self._vAcc

    @property
    def hAcc(self):
        return self._vAcc


# Receive clock data from GPS
class NavTimeUTC(ReceivedPacket):
    """ Receive packet with the utc time solution from the gps. """
    id = 0x2101
    longname = 'UTC Time Solution'

    def __init__(self, payload):
        self._iTOW, self._tAcc, self._nano, self._year, self._month, self._day, self._hour, self._min, self._sec, valid \
            = struct.unpack('<LLlHBBBBBB', payload)
        self._validUTC, self._validWKN, self._validTOW = x2bool(3, valid)
        self._utcStandard = (valid & 0xf0) >> 4
        self._payload = payload

    def __str__(self):
        return (f'Received Packet:     {self.longname}, ID: {self.id}\n' 
                f'Datetime:            {self.time_dt}\n' 
                f'J2000:               {self.time_j2000}\n' 
                f'iTOW (millisecond time of week): {self.iTOW}\n' 
                f'Time Accuracy:       {self.tAcc}\n' 
                f'UTC Standard:        {self.utcStandard}\n'
                f'Valid UTC?:          {self.validUTC}\n'
                f'Valid Week Number?:  {self.validWKN}\n'
                f'Valid Time of Week?: {self.validTOW}\n')

    @property
    def time_dt(self):
        if self._sec == 60:
            return dt.datetime(self._year, self._month, self._day, self._hour, self._min, 59, self._nano // 1000)
        else:
            return dt.datetime(self._year, self._month, self._day, self._hour, self._min, self._sec, self._nano // 1000)

    @property
    def time_j2000(self):
        return (self.time_dt - dt.datetime(2000, 1, 1, 12)).total_seconds()
        # TODO: is this right? probably not

    @property
    def iTOW(self):
        return self._iTOW

    @property
    def tAcc(self):
        return self._tAcc

    @property
    def nano(self):
        return self._nano

    @property
    def year(self):
        return self._year

    @property
    def month(self):
        return self._month

    @property
    def day(self):
        return self._day

    @property
    def hour(self):
        return self._hour

    @property
    def min(self):
        return self._min

    @property
    def sec(self):
        return self._sec

    @property
    def utcStandard(self):
        return self._utcStandard

    @property
    def validUTC(self):
        return self._validUTC

    @property
    def validTOW(self):
        return self._validTOW

    @property
    def validWKN(self):
        return self._validWKN


@dataclass(frozen=True)
class RxmRawxData:
    """ Dataclass for data from each satellite. """
    prMeas: float
    cpMeas: float
    doMeas: float
    gnssId: int
    svId: int
    sigId: int
    freqId: int
    locktime: int
    cno: int
    prStdev: float
    cpStdev: float
    doStdev: float
    subHalfCyc: bool
    halfCyc: bool
    cpValid: bool
    prValid: bool
    key: str


class RxmRawx(ReceivedPacket):
    """ Receive packet for raw GPS data from multiple GNSS types. """
    id = 0x1502
    longname = 'Multi GNSS raw measurement data'

    def __init__(self, payload):
        self._rcvTow, self._week, self._leapS, self._numMeas, recStat, self._version, _ = \
            struct.unpack('dHbBBBH', payload[0:16])
        tmp = x2bool(2, recStat)
        self._leapSecBool, self._clkResetBool = tmp[0], tmp[1]
        dc = []

        for i in range(self._numMeas):
            pr_tmp, cp_tmp, do_tmp, gnss_tmp, sv_tmp, sig_tmp, freq_tmp, locktime_tmp, cno_tmp, prSt_tmp, cpSt_tmp, \
            doSt_tmp, trkSt_tmp, _ = struct.unpack('<ddfBBBBHBBBBBB', payload[16+32*i:48+32*i])

            prSt_tmp = prSt_tmp & 0x0f
            prSt_tmp = 0.01 * 2**prSt_tmp
            cpSt_tmp = cpSt_tmp & 0x0f
            cpSt_tmp = cpSt_tmp * .004
            doSt_tmp = doSt_tmp & 0x0f
            doSt_tmp = 0.02 * 2**doSt_tmp

            id_ = _LOOKUP_GPS[gnss_tmp]
            if id_ == 'R' and sv_tmp == 255:
                key = ''
            else:
                if id_ == 'S':
                    id2 = sv_tmp - 100
                else:
                    id2 = sv_tmp
                key = f'{id_}{id2:02d}'

            dc.append(RxmRawxData(pr_tmp, cp_tmp, do_tmp, gnss_tmp, sv_tmp, sig_tmp, freq_tmp, locktime_tmp, cno_tmp,
                                        prSt_tmp, cpSt_tmp, doSt_tmp, *x2bool(4, trkSt_tmp), key))
        dd = defaultdict(list)
        self._satellites = []
        for i in dc:
            dd[i.key].append(i)
        for i in dd.items():
            i[1].sort(key=lambda x: x.sigId)
            self._satellites.append(i[1])
        self._satellites.sort(key=lambda x: x[0].key)

    def __str__(self):
        return (f'Received Packet:     {self.longname}, ID: {self.id}\n' 
                f'Receiver Time of Week:    {self.rcvTow}\n' 
                f'Week Number               {self.week}\n' 
                f'Leap Second offset:       {self.leapS}\n' 
                f'Number of Measurements:   {self.numMeas}\n' 
                f'Leap seconds determined?: {self.leapSecBool}\n'
                f'Clock reset applied?:     {self.clkResetBool}\n'
                f'Satellite Measurements:   {self.satellites}\n')

    @property
    def rcvTow(self):
        return self._rcvTow
    
    @property
    def week(self):
        return self._week
    
    @property
    def leapS(self):
        return self._leapS
    
    @property
    def numMeas(self):
        return self._numMeas
    
    @property
    def version(self):
        return self._version

    @property
    def leapSecBool(self):
        return self._leapSecBool

    @property
    def clkResetBool(self):
        return self._clkResetBool

    @property
    def satellites(self):
        return [sat for sublist in self._satellites for sat in sublist]
