from setuptools import setup, find_packages
import os
import re


def read(filename):
    with open(os.path.join(os.path.dirname(__file__), filename)) as infile:
        text = infile.read()
    return text


def read_version(filename):
    return re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
            read(filename), re.MULTILINE).group(1)


setup(
    name='ublox',
    version=read_version('ublox/__init__.py'),
    author='Adam Dodge',
    author_email='Adam.Dodge@Colorado.edu',
    description='Set of tools for receiving data from F9P GPS. ',
    long_description=read('README.rst'),
    scripts=['bin/ublox'],
    license='custom',
    url='https://github.com/ccarocean/ublox',
    packages=find_packages(),
    install_requires=[
        'pyserial',
        'astropy',
        'dataclasses;python_version=="3.6"',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: GIS'
    ],
    zip_safe=False
)
