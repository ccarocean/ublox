UBLOX GPS Reader for F9P
========================
Title: ublox

Options
-------


Installation
------------
Create virtual environment and activate:

.. code-block::

    python -m venv --prompt=ublox .venv
    source .venv/bin/activate

Inside Virtual Environment:

.. code-block::

    setup.py install


How to run
----------
Source Virtual Environment:

.. code-block::

    source .venv/bin/activate

Run as root:

.. code-block::

    sudo .venv/bin/python -m ublox
    sudo ublox


Related Files
-------------
- Private key for station must be located in /home/ccaruser/keys
- Raw data directory must exist at /home/ccaruser/data/rawgps
- Position data directory must exist at /home/ccaruser/data/position


Author
------
Adam Dodge

University of Colorado Boulder

Colorado Center for Astrodynamics Research

Jet Propulsion Laboratory

Purpose
-------
This program runs on a raspberry pi and reads data from a SparkFun GPS-RTK2 Board with the ZED-F9P GPS chip. It
initializes the GPS using a specified config file (or default.ini), and can use either UART or USB. It then sends a
post API request to send the data to the web server located at cods.colorado.edu where the data is stored and analyzed.
The data is also stored onboard as a backup. The program also blinks an LED to show someone that the program is running
just by looking at the unit.