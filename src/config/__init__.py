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
    dirs = [
        Settings.get('DIR', 'LOG'),
        Settings.get('MODS_PATH', 'FA'),
        Settings.get('ENGINE_PATH', 'FA'),
        Settings.get('MAPS_PATH', 'FA')
    ]
    for d in dirs:
        if not os.path.isdir(d):
            os.makedirs(d)

v = version.get_git_version()

if getattr(sys, 'frozen', False):
    if not version.is_prerelease_version(v):
        logging.warning("FAF version: " + repr(version.get_git_version()))
        from production import defaults
        make_dirs()
        rotate = RotatingFileHandler(filename=os.path.join(Settings.get('DIR', 'LOG'), 'forever.log'),
                                     maxBytes=Settings.get('MAX_SIZE', 'LOG'),
                                     backupCount=10)
        rotate.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))
        logging.getLogger().addHandler(rotate)
        logging.getLogger().setLevel(Settings.get('LEVEL', 'LOG'))
    else:
        logging.warning("FAF prerelease version: " + repr(version.get_git_version()))
        from develop import defaults
        make_dirs()
        rotate = RotatingFileHandler(filename=os.path.join(Settings.get('DIR', 'LOG'), 'forever.log'),
                                     maxBytes=Settings.get('MAX_SIZE', 'LOG'),
                                     backupCount=10)
        rotate.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))
        logging.getLogger().addHandler(rotate)
        logging.getLogger().setLevel(Settings.get('LEVEL', 'LOG'))
else:
    # Setup logging output
    devh = logging.StreamHandler()
    devh.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))
    logging.getLogger().addHandler(devh)
    logging.getLogger().setLevel(logging.INFO)

    for k in []:
        logging.getLogger(k).setLevel(logging.DEBUG)

    from develop import defaults
    make_dirs()
    logging.warning("FAF development version: " + repr(version.get_git_version()))
