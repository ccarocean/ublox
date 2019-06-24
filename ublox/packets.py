import struct
import numpy as np
import datetime as dt


def raw_packet(dayhour, messages):
    time_header = int((dayhour - dt.datetime(1970, 1, 1)).total_seconds())
    packet = struct.pack('<q', time_header)
    for i in messages:
        header = struct.pack('<dHbB', i.rcvTow, i.week, i.leapS, i.numMeas)
        data = b''
        for j in i.satellites:
            cno = min(max(int(j.cno/6), 1), 9)
            other = ((j.gnssId & 0x07) << 12) | ((j.svId & 0x3f) << 6) | ((j.sigId & 0x07) << 3) | (cno & 0x07)
            data = data + struct.pack('<ddfH', j.prMeas, j.cpMeas, j.doMeas, other)
        packet = packet + header + data
    return packet


def pos_packet(dayhour, messages, week):
    time_header = int((dayhour - dt.datetime(1970, 1, 1)).total_seconds())
    itow = int(np.mean([i.iTOW for i in messages]))
    lon = np.mean([i.lon for i in messages])
    lat = np.mean([i.lat for i in messages])
    height = np.mean([i.height for i in messages])
    return struct.pack('<qIHddd', time_header, itow, week, lon, lat, height)
