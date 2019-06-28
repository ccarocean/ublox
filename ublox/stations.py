import os


def read_key(fname):
    """ Function to read key from file. """
    try:
        with open(fname, 'r') as f:
            key = f.read()
    except FileNotFoundError:
        print('Incorrect key file location. ')
        os._exit(1)
    return key


STATIONS = {'harv': {'public-key':   read_key('../lidar-read/harv.key.pub'),
                     'private-key':  read_key('../lidar-read/harv.key'),
                     'lat':          34.468333,
                     'lon':          360 - 120.671667,
                     'alt':          0
                     }
            }
