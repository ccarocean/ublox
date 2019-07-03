import requests
import jwt
import datetime as dt
import struct
import numpy as np
import os


def call_send(url, key, data, t, cache):
    """ Function for calling send and checking if packet is sent. This is threaded to speed up data collection. """

    for i in cache:
        count = 0
        while not send(url, key, cache[i], 'Old ') and count < 10:
            count += 1
        if count < 10:
            del cache[i]

    count = 0
    while not send(url, key, data, 'New ') and count < 10:
        count += 1
    if count == 10:
        cache[bytes(str(t), 'utf-8')] = data
        print('No connection made. Data saved to cache. ')


def send(url, key, data, s):
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
    print(s + url[-11:-5].upper() + " Packet sent at", dt.datetime.utcnow())
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
            for k in j:
                cno = min(max(int(k.cno/6), 1), 9)  # Turn SNR into integer from 1 to 9
                # Create 2 byte data value with four values combined:
                #       Most significant bit:               Not used
                #       Next three most significant bits:   gnssId
                #       Next 6 bits:                        svId
                #       Next three bits:                    sigId
                #       Next three bits:                    signal to noise ratio transformed to integer between 1 and 9
                other = ((k.gnssId & 0x07) << 12) | ((k.svId & 0x3f) << 6) | ((k.sigId & 0x07) << 3) | (cno & 0x07)
                # Pack all data for each satellite
                packet = packet + struct.pack('<ddfH', k.prMeas, k.cpMeas, k.doMeas, other)
    return packet


def pos_packet(messages, week, leapS):
    """ This functon creates a packet from the high precision position data to be sent to the web server. It only sends
        one averaged packet per minute. """
    itow = int(np.mean([i.iTOW for i in messages]) - leapS*1000)  # GPS time of week average
    lon = np.mean([i.lon for i in messages])  # longitude average
    lat = np.mean([i.lat for i in messages])  # latitude average
    height = np.mean([i.height for i in messages])  # Height above ellipsoid average
    return struct.pack('<IHddd', itow, week, lon, lat, height)  # Return packet
