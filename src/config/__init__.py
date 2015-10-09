from . import version

import os
import sys
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
    if not os.path.isdir(Settings.get('MODS_PATH', 'FA')):
        os.makedirs(Settings.get('MODS_PATH', 'FA'))
    if not os.path.isdir(Settings.get('ENGINE_PATH', 'FA')):
        os.makedirs(Settings.get('ENGINE_PATH', 'FA'))
    if not os.path.isdir(Settings.get('MAPS_PATH', 'FA')):
        os.makedirs(Settings.get('MAPS_PATH', 'FA'))

v = version.get_git_version()

if os.getenv("FAF_FORCE_PRODUCTION") or getattr(sys, 'frozen', False) and not version.is_prerelease_version(v):
    from production import defaults
    make_dirs()
    rotate = RotatingFileHandler(filename=os.path.join(Settings.get('DIR', 'LOG'), 'forever.log'),
                                 maxBytes=Settings.get('MAX_SIZE', 'LOG'),
                                 backupCount=10)
    rotate.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))
    logging.getLogger().addHandler(rotate)
    logging.getLogger().setLevel(Settings.get('LEVEL', 'LOG'))
elif version.is_development_version(v)\
        or sys.executable.endswith("py.test"):
    # Setup logging output
    devh = logging.StreamHandler()
    devh.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))
    logging.getLogger().addHandler(devh)
    logging.getLogger().setLevel(logging.INFO)

    for k in []:
        logging.getLogger(k).setLevel(logging.DEBUG)

    from develop import defaults
    make_dirs()
elif version.is_prerelease_version(v):
    from develop import defaults
    make_dirs()
    rotate = RotatingFileHandler(filename=os.path.join(Settings.get('DIR', 'LOG'), 'forever.log'),
                                 maxBytes=Settings.get('MAX_SIZE', 'LOG'),
                                 backupCount=10)
    rotate.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))
    logging.getLogger().addHandler(rotate)
    logging.getLogger().setLevel(Settings.get('LEVEL', 'LOG'))

logging.getLogger().info("FAF version: {}".format(version.get_git_version()))
