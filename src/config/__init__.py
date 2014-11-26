__author__ = 'Sheeo'

import os
import sys
import version
import logging
from logging.handlers import RotatingFileHandler
from PyQt4 import QtCore

_settings = QtCore.QSettings("ForgedAllianceForever", "FA Lobby")


class Settings(object):
    """
    This wraps QSettings, fetching default values from the
    selected configuration module if the key isn't found.
    """
    @staticmethod
    def get(key, group=None):
        if group is None:
            value = _settings.value(key)
        else:
            _settings.beginGroup(group)
            value = _settings.value(key)
            _settings.endGroup()
        if value is None:
            if group is None:
                return defaults[key]
            else:
                return defaults[group][key]
        return value

    @staticmethod
    def set(key, value, group=None):
        if group is None:
            _settings.setValue(key, value)
        else:
            _settings.beginGroup(group)
            _settings.setValue(key, value)
            _settings.endGroup()


def make_dirs():
    if not os.path.isdir(Settings.get('DIR', 'LOG')):
        os.makedirs(Settings.get('DIR', 'LOG'))


def rotate_logs():
    log_dir = Settings.get('DIR', 'LOG')
    faf_log_file = os.path.join(log_dir, 'forever.log')
    # Same dirty implementation for now
    if os.path.isfile(faf_log_file) and os.path.getsize(faf_log_file) > Settings.get('MAX_SIZE', 'LOG'):
        os.remove(faf_log_file)


if version.is_development_version()\
        or sys.executable.endswith('py.test')\
        or sys.executable.endswith('python.exe'):
    # Setup logging output
    devh = logging.StreamHandler()
    devh.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))
    logging.getLogger().addHandler(devh)
    logging.getLogger().setLevel(logging.INFO)

    for k in []:
        logging.getLogger(k).setLevel(logging.DEBUG)

    logging.info("Loading development configuration")
    from develop import defaults
    make_dirs()
    rotate_logs()
    logging.warning("FAF development version: " + repr(version.get_git_version()))
else:
    from production import defaults
    make_dirs()
    rotate = RotatingFileHandler(filename=os.path.join(Settings.get('DIR', 'LOG'), 'forever.log'),
                                 maxBytes=Settings.get('MAX_SIZE', 'LOG'),
                                 backupCount=10)
    rotate.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))
    logging.getLogger(rotate)
    logging.getLogger().setLevel(Settings.get('LEVEL', 'LOG'))
    logging.warning("FAF version: " + repr(version.get_git_version()))

