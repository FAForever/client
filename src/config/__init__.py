from . import version
import os
import sys
import logging
import trueskill
from logging.handlers import RotatingFileHandler
from PyQt4 import QtCore

trueskill.setup(mu=1500, sigma=500, beta=250, tau=5, draw_probability=0.10)

_settings = QtCore.QSettings(QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, "ForgedAllianceForever", "FA Lobby")
_unpersisted_settings = {}


class Settings:
    """
    This wraps QSettings, fetching default values from the
    selected configuration module if the key isn't found.
    """

    @staticmethod
    def get(key, default=None, type=str):
        # Get from a local dict cache before hitting QSettings
        # this is for properties such as client.login which we
        # don't necessarily want to persist
        if key in _unpersisted_settings:
            return _unpersisted_settings[key]
        # Hit QSettings to see if the user has defined a value for the key
        if _settings.contains(key):
            return _settings.value(key, type=type)
        # Try out our defaults for the current environment
        return defaults.get(key, default)

    @staticmethod
    def set(key, value, persist=True):
        _unpersisted_settings[key] = value
        if not persist:
            _settings.remove(key)
        else:
            _settings.setValue(key, value)

    @staticmethod
    def persisted_property(key, default_value=None, persist_if=lambda self: True, type=str):
        """
        Create a magically persisted property

        :param key: QSettings key to persist with
        :param default_value: default value
        :param persist_if: Lambda predicate that gets self as a first argument.
                           Determines whether or not to persist the value
        :param type: Type of values for persisting
        :return: a property suitable for a class
        """
        return property(lambda s: Settings.get(key, default=default_value, type=type),
                        lambda s, v: Settings.set(key, v, persist=persist_if(s)),
                        doc='Persisted property: {}. Default: '.format(key, default_value))


def make_dirs():
    if not os.path.isdir(Settings.get('client/data_path')):
        os.makedirs(Settings.get('game/data_path'))
    if not os.path.isdir(Settings.get('game/logs/path')):
        os.makedirs(Settings.get('game/logs/path'))
    if not os.path.isdir(Settings.get('game/mods/path')):
        os.makedirs(Settings.get('game/mods/path'))
    if not os.path.isdir(Settings.get('game/engine/path')):
        os.makedirs(Settings.get('game/engine/path'))
    if not os.path.isdir(Settings.get('game/maps/path')):
        os.makedirs(Settings.get('game/maps/path'))


VERSION = version.get_git_version()


def is_development_version():
    return version.is_development_version(VERSION)


# FIXME: Don't initialize proxy code that shows a dialogue box on import
no_dialogs = False

if os.getenv("FAF_FORCE_PRODUCTION") or getattr(sys, 'frozen', False) and not version.is_prerelease_version(VERSION):
    from production import defaults

    make_dirs()
    rotate = RotatingFileHandler(filename=os.path.join(Settings.get('client/logs/path'), 'forever.log'),
                                 maxBytes=Settings.get('client/logs/max_size'),
                                 backupCount=10)
    rotate.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))
    logging.getLogger().addHandler(rotate)
    logging.getLogger().setLevel(Settings.get('client/logs/level'))
elif is_development_version() or sys.executable.endswith("py.test"):
    # Setup logging output
    devh = logging.StreamHandler()
    devh.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))
    logging.getLogger().addHandler(devh)
    logging.getLogger().setLevel(logging.INFO)

    for k in []:
        logging.getLogger(k).setLevel(logging.DEBUG)

    from develop import defaults

    make_dirs()
elif version.is_prerelease_version(VERSION):
    from develop import defaults

    make_dirs()
    rotate = RotatingFileHandler(filename=os.path.join(Settings.get('client/logs/path'), 'forever.log'),
                                 maxBytes=Settings.get('client/logs/max_size'),
                                 backupCount=10)
    rotate.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))
    logging.getLogger().addHandler(rotate)
    logging.getLogger().setLevel(Settings.get('client/logs/level'))

logging.getLogger().info("FAF version: {}".format(version.get_git_version()))
