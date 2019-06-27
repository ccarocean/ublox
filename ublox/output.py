import datetime as dt
import os
import sys
import numpy as np


# Lookup tables for names and GPS identifiers.
_LOOKUP = {'harv': 'Harvest Oil Platform', 'cata': 'Catalina Island', 'ucbo': 'University of Colorado Boulder'}
_LOOKUP_GPS = {0: 'G', 1: 'S', 2: 'E', 3: 'C', 6: 'R'}


def fix_rinex(f):
    """ function for checking and fixing a rinex file in case something happened to the process mid write. """
    num_data = 132
    with open(f, 'r+') as file:
        d = file.readlines()
        if len(d) <= 23:  # Ensure file has more than just header, otherwise delete
            os.remove(f)
        else:
            file.seek(0)
            ind = [i for i, s in enumerate(d) if '>' in s]
            ind_lastmeas = ind[-1]
            for i in d[:ind_lastmeas]:  # Write all but last measurement
                file.write(i)
            try:
                numsats = int(d[ind_lastmeas].split()[-1])
            except ValueError:
                file.truncate()
                return
            # Ensure last measurement is good before writing it.
            if numsats == (len(d)-ind_lastmeas-1) and len(d[-1]) == num_data:
                for i in d[ind_lastmeas:]:
                    file.write(i)
            file.truncate()  # Delete unwritten data


def fix_hppos(f):
    """ function to check and fix a high precision position file. """
    with open(f, 'r+') as file:
        d = file.readlines()
        file.seek(0)
        for i in d[:-1]:  # Write all but last line
            file.write(i)
        l = d[-1].split(' ')
        if len(l) == 5:  # If final line is complete, write it too
            file.write(d[-1])
        file.truncate()  # Remove bad stuff


class RinexWrite:
    """ Class for writing a rinex file using raw gps data from the F9P. """
    def __init__(self, directory, lat, lon, alt, week, tow, leapS, station='harv'):
        self.t = dt.datetime(1980, 1, 6) + \
                 dt.timedelta(days=7*week, seconds=int(tow), microseconds=(tow-int(tow))*10**6)

        self.fname = os.path.join(directory, self.t.strftime(station + '%j0.%yO'))
        self.station = station
        self.longname = _LOOKUP[station]
        self.lat = lat
        self.lon = lon
        self.alt = alt
        self.content = ''
        self.leapS = leapS
        if os.path.isfile(self.fname):
            fix_rinex(self.fname)
        if not os.path.isfile(self.fname):
            self.write_header()

    def write_header(self, *, version=3.01, file_type='O: Observation', satellite_type='M: Mixed GNSS',
                     run_by='GPSLiDAR', organization='CCAR', observer='Adam Dodge', agency='CCAR', receiver_num='1',
                     receiver_type='GENERIC_P1', receiver_vers='1.0.0', antenna_number=1, antenna_type='RTK2-F9P',
                     delta_pos=[0,0,0]):
        """ Function to write RINEX Header. A lot is hard coded so if someone wanted to use it for something else they
            would need to make a relatively large amount of changes. """
        markerstr = 'GPS LiDAR System at ' + self.longname
        if not os.path.isfile(self.fname):
            tstr = self.t.strftime('%Y%m%d %H%M%S')
            # TODO: Fix header (not working in readers)
            r = 6371000 + self.alt
            x = r * np.cos(self.lat * np.pi/180) * np.cos(self.lon * np.pi/180)
            y = r * np.cos(self.lat * np.pi/180) * np.sin(self.lon * np.pi/180)
            z = r * np.sin(self.lat * np.pi/180)
            header = f'{version:>9.2f}{" ":<11s}{file_type:<20s}{satellite_type:<20s}{"RINEX VERSION / TYPE":<20s}\n' + \
                     f'{run_by:<20s}{organization:<20s}{tstr:<16s}UTC {"PGM / RUN BY / DATE":<20s}\n' + \
                     f'{markerstr:<60}{"MARKER NAME":<20s}\n' + \
                     f'{self.station:<60}{"MARKER NUMBER":<20s}\n' + \
                     f'{"GEODETIC":<20s}{" ":40s}{"MARKER TYPE":<20s}\n' + \
                     f'{observer:<20}{agency:<40}{"OBSERVER / AGENCY":<20s}\n' + \
                     f'{receiver_num:<20}{receiver_type:<20}{receiver_vers:<20}{"REC # / TYPE / VERS":<20s}\n' + \
                     f'{antenna_number:<20}{antenna_type:<40s}{"ANT # / TYPE":<20s}\n' + \
                     f'{x:14.4f}{y:>14.4f}{z:>14.4f}{" ":18s}{"APPROX POSITION XYZ":<20s}\n' + \
                     f'{delta_pos[0]:14.4f}{delta_pos[1]:>14.4f}{delta_pos[2]:>14.4f}{" ":18s}{"ANTENNA: DELTA H/E/N":<20s}\n' + \
                     f'G  {8:<3d} C1  L1  D1  S1  C2  L2  D2  S2                       {"SYS / # / OBS TYPES":<20s}\n' + \
                     f'R  {8:<3d} C1  L1  D1  S1  C2  L2  D2  S2                       {"SYS / # / OBS TYPES":<20s}\n' + \
                     f'E  {8:<3d} C1  L1  D1  S1  C2  L2  D2  S2                       {"SYS / # / OBS TYPES":<20s}\n' + \
                     f'S  {8:<3d} C1  L1  D1  S1  C5  L5  D5  S5                       {"SYS / # / OBS TYPES":<20s}\n' + \
                     f'{"DBHZ":<60s}{"SIGNAL STRENGTH UNIT":<20s}\n' + \
                     f'{self.t.year:>6d}{self.t.month:>6d}{self.t.day:>6d}{self.t.hour:>6d}{self.t.minute:>6d}' + \
                         f'{self.t.second:>13.7f}     UTC{" ":<9s}{"TIME OF FIRST OBS":<20s}\n' + \
                     f'     0{" ":54s}{"RCV CLOCK OFFS APPL":<20s}\n' + \
                     f'G{" ":<59}{"SYS / PHASE SHIFTS":<20s}\n' + \
                     f'R{" ":<59}{"SYS / PHASE SHIFTS":<20s}\n' + \
                     f'E{" ":<59}{"SYS / PHASE SHIFTS":<20s}\n' + \
                     f'S{" ":<59}{"SYS / PHASE SHIFTS":<20s}\n' + \
                     f'{self.leapS:>6d}{" ":>54s}{"LEAP SECONDS":<20s}\n' + \
                     f'{" ":>60s}{"END OF HEADER":<20s}\n'

            try:
                with open(self.fname, 'w') as f:
                    f.write(header)
            except FileNotFoundError:
                print('Bad data directory. Try again.')
                sys.exit(0)

    def write_data(self, packet):
        """ Function to write gps measurement to RINEX file. """
        # TODO: check frequency instead of just doing one and two - could only be 2
        if not packet.satellites:
            return  # No satellites
        t = dt.datetime(1980, 1, 6) + \
            dt.timedelta(days=7*packet.week, seconds=int(packet.rcvTow),
                         microseconds=(packet.rcvTow - int(packet.rcvTow))*10**6) - \
            dt.timedelta(seconds=packet.leapS)
        epoch = f'> {t.year:4d} {t.month:02d} {t.day:02d} {t.hour:2d} {t.minute:2d} ' \
                f'{t.second + t.microsecond*10**-6:11.7f}  0{len(packet.satellites):>3d}{" ":<44}\n'
        line = ''
        for s in packet.satellites:
            snr0 = s[0].cno
            if s[0].key == '':
                pass
            else:
                line = line + f'{s[0].key:3s}{s[0].prMeas:>14.3f} {snr0:>1d}{s[0].cpMeas:>14.3f} {snr0:>1d}' \
                              f'{s[0].doMeas:>14.3f} {snr0:>1d}{s[0].cno:>14.3f} {snr0:>1d}'
            if len(s) == 2:  # If L1 and L2 Frequencies
                snr1 = min(max(int(s[1].cno/6), 1), 9)
                line = line + f'{s[1].prMeas:>14.3f} {snr1:>1d}{s[1].cpMeas:>14.3f} {snr1:>1d}{s[1].doMeas:>14.3f} ' \
                              f'{snr1:>1d}{s[1].cno:>14.3f} {snr1:>1d}\n'

            else:
                line = line + f'{0.0:>14.3f}  {0.0:>14.3f}  {0.0:>14.3f}  {0.0:>14.3f}  \n'

        try:
            with open(self.fname, 'a') as f:
                f.write(epoch + line)
        except FileNotFoundError:
            print('Bad data directory. Try again.')
            sys.exit(0)