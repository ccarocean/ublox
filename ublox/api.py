import requests
import jwt
import datetime as dt
import struct
import numpy as np
import os


def write_unsent(fname, l, data):
    try:
        with open(fname, 'ab') as f:
            f.write(struct.pack('<H', l) + data)
        return False
    except FileNotFoundError:
        print('Not Sent Directory does not exist. ')
        os._exit(1)


def call_send(url, key, data):
    """ Function for calling send and checking if packet is sent. This is threaded to speed up data collection. """
    count = 0
    fname = '/home/ccaruser/not-sent/' + url[-11:-5] + '.bin'

    # Check if there is old unsent data
    with open(fname, 'r+b') as f:
        d = f.read()

    with open(fname, 'w') as f:
        f.write('')

    if len(d) > 2:
        n = struct.unpack('<H', d[0:2])[0]
        ind = 2
        while ind + n <= len(d):
            n = struct.unpack('<H', d[ind-1:ind])[0]
            while not send(url, key, d[ind:ind+n]) and count < 100:
                count += 1
            if count == 100:
                write_unsent(fname, n, d[ind:ind+n])
            ind = ind + n + 2

    while not send(url, key, data) and count < 100:
        count += 1
    if count == 100:
        write_unsent(fname, len(data), data)


def send(url, key, data):
    """ Function for sending packet.
        This returns true if it receives a 201 code and false if it receives any other code. """
    headers = {"Content-Type": "application/octet-stream",
               "Bearer": sign(key)}
    try:
        upload = requests.post(url, data=data, headers=headers)
    except:
        return False
    if upload.status_code != 201:
        return False
    return True


def sign(key):
    """ This function signs the data with the private key of the given location. """
    return jwt.encode({'t': str((dt.datetime.utcnow()-dt.datetime(1970, 1, 1)).total_seconds())}, key,
                      algorithm='RS256')


def raw_packet(messages):
    """ This function creates a packet from the raw data to be sent to the web server. """
    packet = b''
    for i in messages:  # For each data point in minute of data
        packet = packet + struct.pack('<dHbB', i.rcvTow, i.week, i.leapS, i.numMeas)  # Pack single data point values
        for j in i.satellites:  # For each satellite
            cno = min(max(int(j.cno/6), 1), 9)  # Turn SNR into integer from 1 to 9
            # Create 2 byte data value with four values combined:
            #       Most significant bit:                   Not used
            #       Next three most significant bits:       gnssId
            #       Next 6 bits:                            svId
            #       Next three bits:                        sigId
            #       Next three bits:                        signal to noise ratio transformed to integer between 1 and 9
            other = ((j.gnssId & 0x07) << 12) | ((j.svId & 0x3f) << 6) | ((j.sigId & 0x07) << 3) | (cno & 0x07)
            # Pack all data for each satellite
            packet = packet + struct.pack('<ddfH', j.prMeas, j.cpMeas, j.doMeas, other)
    return packet


def pos_packet(messages, week, leapS):
    """ This functon creates a packet from the high precision position data to be sent to the web server. It only sends
        one averaged packet per minute. """
    itow = int(np.mean([i.iTOW for i in messages]) - leapS*1000)  # GPS time of week average
    lon = np.mean([i.lon for i in messages])  # longitude average
    lat = np.mean([i.lat for i in messages])  # latitude average
    height = np.mean([i.height for i in messages])  # Height above ellipsoid average
    return struct.pack('<IHddd', itow, week, lon, lat, height)  # Return packet
