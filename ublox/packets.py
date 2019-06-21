import struct
import numpy as np


def raw_packet(messages):
    packet = b''
    for i in messages:
        unixtime = 0  # TODO
        header = struct.pack('<qdHbB', unixtime, i.rcvTow, i.week, i.leapS, i.numMeas)
        data = b''
        for j in i.satellites:
            cno = min(max(int(j.cno/6), 1), 9)
            other = ((j.gnssId & 0x07) << 12) | ((j.svId & 0x3f) << 6) | ((j.sigId & 0x07) << 3) | (cno & 0x07)
            data = data + struct.pack('<ddfH', j.prMeas, j.cpMeas, j.doMeas, other)
        packet = packet + header + data
    return packet


def pos_packet(messages, week):
    itow = int(np.mean([i.iTOW for i in messages]))
    unixtime = 0  # TODO
    lon = np.mean([i.lon for i in messages])
    lat = np.mean([i.lat for i in messages])
    height = np.mean([i.height for i in messages])
    #import pdb; pdb.set_trace()
    return struct.pack('<qIHddd', unixtime, itow, week, lon, lat, height)
