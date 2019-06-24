import serial
import numpy as np
import datetime as dt
import argparse
from configparser import ConfigParser
from threading import Thread
from .ublox_reader import UBXReader
from .ublox_writer import UBXWriter
from .messages import NavTimeUTC, NavHPPOSLLH, AckAck, AckNak, CfgValgetRec, RxmRawx, InfDebug, InfError, InfNotice, \
                      InfTest, InfWarning, CfgValsetSend
from .api import call_send
from .led import LED
from .packets import pos_packet, raw_packet

# DOWNLOAD EPHEMERIS: (2019 is year, 168 is day of year, 0 means daily, 19 is year, and n means navigation)
# wget ftp://cddis.nasa.gov/gnss/data/hourly/2019/168/hour1680.19n.Z


def read_key(fname):
    with open(fname, 'r') as f:
        key = f.read()
    return key


def main():
    port = '/dev/serial/by-id/usb-u-blox_AG_-_www.u-blox.com_u-blox_GNSS_receiver-if00'
    url = ' http://127.0.0.1:5000/'
    comm_type = 'USB'
    cfile = 'default.ini'
    msg_dict = {NavTimeUTC.id: NavTimeUTC,
                NavHPPOSLLH.id: NavHPPOSLLH,
                AckAck.id: AckAck,
                AckNak.id: AckNak,
                CfgValgetRec.id: CfgValgetRec,
                RxmRawx.id: RxmRawx,
                InfDebug.id: InfDebug,
                InfError.id: InfError,
                InfNotice.id: InfNotice,
                InfTest.id: InfTest,
                InfWarning.id: InfWarning}

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--comm', type=str, default=comm_type,
                        help='Communication type ("USB" or "UART"). Default is "' + comm_type + '"')
    parser.add_argument('-f', '--configfile', type=str, default=cfile,
                        help='Location of configuration file to use. Default is "' + cfile + '"')
    parser.add_argument('-p', '--port', type=str, default=port,
                        help='Port where GPS is connected. Default is: \n"' + port + '"')
    args = parser.parse_args()

    dev = serial.Serial(args.port,
                        timeout=5,
                        baudrate=38400,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS)

    # Configure
    config = ConfigParser(inline_comment_prefixes=('#', ';'))
    config.read(args.configfile)

    packet = CfgValsetSend(config[args.comm])

    # Write config packet
    wrtr = UBXWriter(dev, msg_dict)
    wrtr.write_packet(packet.payload(), packet.id)

    try:
        dev.baudrate = config[args.comm]['CFG-UART1-BAUDRATE']
    except KeyError:
        pass

    # Read packets
    i = 0

    loc = 'harv'
    keys = {'harv': read_key('../lidar-read/harv.key')}
    week = False
    led = LED(15)
    led.switch()
    try:
        while True:
            led_timer = dt.datetime.utcnow()
            now = dt.datetime.utcnow()
            min = dt.datetime(now.year, now.month, now.day, now.hour, now.minute)
            dayhour = dt.datetime(now.year, now.month, now.day, now.hour)
            end = min + dt.timedelta(minutes=1)
            print('Now: ', now)
            print('End: ', end)
            raw, hp_pos, t = [], [], []
            while dt.datetime.utcnow() < end:
                rdr = UBXReader(dev, msg_dict)
                packet = rdr.read_packet()
                if isinstance(packet, RxmRawx):
                    raw.append(packet)
                    week = packet.week
                elif isinstance(packet, NavHPPOSLLH):
                    hp_pos.append(packet)
                elif isinstance(packet, NavTimeUTC):
                    # TODO: Set system Time
                    t.append(packet)
                else:
                    pass
                if (dt.datetime.now() - led_timer).total_seconds() >= 1:
                    led.switch()
                    led_timer = dt.datetime.now()
            # Get packets to send
            print("Packet sending at", dt.datetime.utcnow())
            if raw:
                p_raw = raw_packet(dayhour, raw)
                t2 = Thread(target=call_send, args=(url + 'rawgps/' + loc, keys[loc], p_raw,))
                t2.start()

            if hp_pos and week:
                p_pos = pos_packet(dayhour, hp_pos, week)
                t3 = Thread(target=call_send, args=(url + 'posgps/' + loc, keys[loc], p_pos,))
                t3.start()

    finally:
        led.set_low()
