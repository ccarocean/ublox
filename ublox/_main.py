import serial
import datetime as dt
import argparse
import sys
import diskcache as dc
from configparser import ConfigParser
from threading import Thread
from .ublox_reader import UBXReader
from .ublox_writer import UBXWriter
from .messages import NavTimeUTC, NavHPPOSLLH, AckAck, AckNak, CfgValgetRec, RxmRawx, InfDebug, InfError, InfNotice, \
                      InfTest, InfWarning, CfgValsetSend
from .api import call_send, pos_packet, raw_packet, save_to_dc, send_old
from .led import LED

# DOWNLOAD EPHEMERIS: (2019 is year, 168 is day of year, 0 means daily, 19 is year, and n means navigation)
# wget ftp://cddis.nasa.gov/gnss/data/hourly/2019/168/hour1680.19n.Z


def read_key(fname):
    """ Function for reading private key for a given location. """
    try:
        with open(fname, 'r') as f:
            key = f.read()
    except FileNotFoundError:
        print("Bad key location. ")
        sys.exit(0)
    return key


def main():
    url = 'https://cods.colorado.edu/api/gpslidar/'
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
                InfWarning.id: InfWarning}  # Dictionary of implemented packet formats

    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--comm', type=str, default="USB",
                        help='Communication type ("USB" or "UART"). Default is "USB"')
    parser.add_argument('-f', '--configfile', type=str, default='default.ini',
                        help='Location of configuration file to use. Default is "default.ini"')
    parser.add_argument('-l', '--location', type=str, help='GPS location. (ex. harv)', required=True)
    parser.add_argument('--led', type=int, default=20, help='LED pin. Default is 20.')
    args = parser.parse_args()

    if args.comm == "USB":
        port = '/dev/serial/by-id/usb-u-blox_AG_-_www.u-blox.com_u-blox_GNSS_receiver-if00'  # Serial port  TODO: UART
    elif args.comm == "UART":
        port = '/dev/ttyS0'

    dev = serial.Serial(port,
                        timeout=5,
                        baudrate=38400,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS)  # Open serial port

    # Configure
    config = ConfigParser(inline_comment_prefixes=('#', ';'))
    config.read(args.configfile)  # Read configuration packets to be sent

    packet = CfgValsetSend(config[args.comm])  # Create configuration packets

    # Write config packet
    wrtr = UBXWriter(dev, msg_dict)  # ublox writer
    wrtr.write_packet(packet.payload(), packet.id)  # Write ublox packets

    try:
        dev.baudrate = config[args.comm]['CFG-UART1-BAUDRATE']  # Set baud rate to desired rate in configuration file
    except KeyError:  # If there is no baud rate in configuration file
        pass

    # Read packets
    loc = args.location
    key = read_key('/home/ccaruser/.keys/' + loc + '.key')  # Private key for sending
    led = LED(args.led)  # LED class initialization
    led.set_high()  # Turn on LED

    next_raw, next_pos = [], []

    leapS = None
    week = None

    cache_raw = dc.Cache('/var/tmp/unsent_gpsraw')
    cache_pos = dc.Cache('/var/tmp/unsent_gpspos')

    # Send old data
    t2 = Thread(target=send_old, args=(cache_raw, url + 'rawgps/' + loc, key))
    t2.start()
    t3 = Thread(target=send_old, args=(cache_pos, url + 'posgps/' + loc, key))
    t3.start()

    print('Starting at:', dt.datetime.utcnow())

    try:
        while True:
            led_timer = dt.datetime.utcnow()
            raw, hp_pos = next_raw, next_pos  # Initialization of vectors
            next_raw, next_pos = [], []
            prev_raw, prev_pos = 0, 0
            while True:
                rdr = UBXReader(dev, msg_dict)  # Initialize reader
                packet = rdr.read_packet()  # Read packet
                if isinstance(packet, RxmRawx):  # If raw gps position packet
                    mod_raw = (packet.rcvTow - packet.leapS) % 60
                    if mod_raw > prev_raw:
                        raw.append(packet)
                        week = packet.week
                        leapS = packet.leapS
                        prev_raw = mod_raw
                    else:
                        next_raw.append(packet)
                        break
                elif isinstance(packet, NavHPPOSLLH) and leapS:  # If high precision gps position packet
                    mod_pos = ((packet.iTOW / 1000) - leapS) % 60
                    if mod_pos > prev_pos:
                        hp_pos.append(packet)
                        prev_pos = mod_pos
                    else:
                        next_pos.append(packet)
                        break
                elif isinstance(packet, NavTimeUTC):  # If time packet
                    time = dt.datetime(packet.year, packet.month, packet.day, packet.hour, packet.min,
                                       packet.sec, packet.nano // 10**3)
                    print(time.strftime('%Y-%m-%d %H:%M:%S UTC'))
                    # TODO: Set system Time
                    pass
                else:
                    pass
                if (dt.datetime.utcnow() - led_timer).total_seconds() >= 1:  # Switch led every second
                    led.switch()
                    led_timer = dt.datetime.utcnow()

            # Get packets to send and start threads to send packets through api

            if raw:
                p_raw = raw_packet(raw)
                if not t2.isAlive():
                    t2 = Thread(target=call_send, args=(url + 'rawgps/' + loc, key, p_raw,
                                                        (dt.datetime.utcnow()-dt.datetime(1970, 1, 1)).total_seconds(),
                                                        cache_raw))
                    t2.start()
                else:
                    save_to_dc(cache_raw, (dt.datetime.utcnow()-dt.datetime(1970, 1, 1)).total_seconds(), p_raw)

            if hp_pos and week and leapS and not t3.is_alive():
                p_pos = pos_packet(hp_pos, week, leapS)
                if not t3.isAlive():
                    t3 = Thread(target=call_send, args=(url + 'posgps/' + loc, key, p_pos,
                                                        (dt.datetime.utcnow()-dt.datetime(1970, 1, 1)).total_seconds(),
                                                        cache_pos))
                    t3.start()
                else:
                    save_to_dc(cache_pos, (dt.datetime.utcnow()-dt.datetime(1970, 1, 1)).total_seconds(), p_pos)

    finally:
        # At the end turn LED off
        led.set_low()
