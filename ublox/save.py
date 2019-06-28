import datetime as dt
import os
import struct
from .output import fix_hppos, RinexWrite


def save_raw_gps(packets, data_directory, loc, lat, lon, alt):
    """ Function for saving raw GPS data to a file. """
    wrtr = RinexWrite(os.path.join(data_directory, loc, 'rawgps'), lat, lon, alt, packets[0].week, packets[0].rcvTow,
                      packets[0].leapS, loc)
    for p in packets:
        wrtr.write_data(p)
    print('Raw GPS data saved locally. ')


def save_gps_pos(data, data_directory, loc):
    """ Function for saving the gps position data. """
    if len(data) != 30:
        print("Data is incorrect. ")
        return
    itow, week, lon, lat, height = struct.unpack('<IHddd', data)
    t = dt.datetime(1980, 1, 6) + dt.timedelta(days=7*week, microseconds=itow*1000)
    fname = os.path.join(data_directory, 'position', t.strftime('%Y-%m-%d.txt'))
    if os.path.isfile(fname):  # If file exists make sure it doesnt need to be fixed
        fix_hppos(fname)
    try:
        with open(fname, 'a+') as f:
            f.write(f'{t} {lat} {lon} {height}\n')  # Write
    except FileNotFoundError:
        print('Data directory is bad. Try again. ')
        os._exit(1)
    print('GPS position data saved locally. ')
