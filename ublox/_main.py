import serial
import datetime as dt
import argparse
from configparser import ConfigParser
from threading import Thread
from .ublox_reader import UBXReader
from .ublox_writer import UBXWriter
from .messages import NavTimeUTC, NavHPPOSLLH, AckAck, AckNak, CfgValgetRec, RxmRawx, InfDebug, InfError, InfNotice, \
                      InfTest, InfWarning, CfgValsetSend
from .api import call_send, pos_packet, raw_packet
from .led import LED

# DOWNLOAD EPHEMERIS: (2019 is year, 168 is day of year, 0 means daily, 19 is year, and n means navigation)
# wget ftp://cddis.nasa.gov/gnss/data/hourly/2019/168/hour1680.19n.Z


def read_key(fname):
    """ Function for reading private key for a given location. """
    with open(fname, 'r') as f:
        key = f.read()
    return key


def main():
    port = '/dev/serial/by-id/usb-u-blox_AG_-_www.u-blox.com_u-blox_GNSS_receiver-if00'  # Serial port  TODO: UART
    url = ' http://127.0.0.1:5000/'  # Temporary web server path - this will be updated with cods eventually
    comm_type = 'USB'  # Type of communication for reading config file. This will eventually be UART
    cfile = 'default.ini'  # Default configuration file
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
    parser.add_argument('-c', '--comm', type=str, default=comm_type,
                        help='Communication type ("USB" or "UART"). Default is "' + comm_type + '"')
    parser.add_argument('-f', '--configfile', type=str, default=cfile,
                        help='Location of configuration file to use. Default is "' + cfile + '"')
    parser.add_argument('-p', '--port', type=str, default=port,
                        help='Port where GPS is connected. Default is: \n"' + port + '"')
    parser.add_argument('-l', '--location', type=str, default='harv', help='GPS location. Default is harv.')
    args = parser.parse_args()

    dev = serial.Serial(args.port,
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
    keys = {'harv': read_key('../lidar-read/harv.key')}  # Dictionary of keys
    week = False
    led = LED(21)  # LED class initialization
    led.switch()  # Turn on LED

    next_raw, next_pos = [], []

    try:
        while True:
            led_timer = dt.datetime.utcnow()
            now = dt.datetime.utcnow()
            min = dt.datetime(now.year, now.month, now.day, now.hour, now.minute)  # Datetime of minute
            dayhour = dt.datetime(now.year, now.month, now.day, now.hour)  # Datetime of day with hour
            end = min + dt.timedelta(minutes=1)  # End of minute to collect data for single packet
            print('Now: ', now)
            print('End: ', end)
            raw, hp_pos, t = next_raw, next_pos, []  # Initialization of vectors
            next_raw, next_pos = [], []
            while dt.datetime.utcnow() < end:
                prev_raw, prev_pos = 0, 0
                rdr = UBXReader(dev, msg_dict)  # Initialize reader
                packet = rdr.read_packet()  # Read packet
                if isinstance(packet, RxmRawx):  # If raw gps position packet
                    mod_raw = (packet.rcvTow - packet.leapS) % 60
                    print(mod_raw, prev_raw)
                    if mod_raw > prev_raw:
                        raw.append(packet)
                        week = packet.week
                        prev_raw = mod_raw
                    else:
                        next_raw.append(packet)
                        break
                elif isinstance(packet, NavHPPOSLLH):  # If high precision gps position packet
                    mod_pos = (packet.iTOW * 1000) % 60
                    print(mod_pos, prev_pos)
                    if mod_pos > prev_pos:
                        hp_pos.append(packet)
                        prev_pos = mod_pos
                    else:
                        next_pos.append(packet)
                        break
                elif isinstance(packet, NavTimeUTC):  # If time packet
                    # TODO: Set system Time
                    t.append(packet)
                else:
                    pass
                if (dt.datetime.now() - led_timer).total_seconds() >= 1:  # Switch led every second
                    led.switch()
                    led_timer = dt.datetime.now()

            # Get packets to send and start threads to send packets through api
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
        # At the end turn LED off
        led.set_low()
