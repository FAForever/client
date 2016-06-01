from . import version
import os
import logging
import trueskill
from PyQt4 import QtCore
from logging.handlers import RotatingFileHandler, MemoryHandler

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
    def remove(key):
        if key in _unpersisted_settings:
            del _unpersisted_settings[key]
        if _settings.contains(key):
            _settings.remove(key)

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
    for dir in [
        'client/data_path',
        'game/logs/path',
        'game/bin/path',
        'game/mods/path',
        'game/engine/path',
        'game/maps/path',
    ]:
        path = Settings.get(dir)
        if path is None:
            raise Exception("Missing configured path for {}".format(dir))
        if not os.path.isdir(path):
            os.makedirs(path)

VERSION = version.get_git_version()


def is_development_version():
    return version.is_development_version(VERSION)


# FIXME: Don't initialize proxy code that shows a dialogue box on import
no_dialogs = False

environment = 'production'


def is_beta():
    return environment == 'development'

if _settings.contains('client/force_environment'):
    environment = _settings.value('client/force_environment', 'development')

if environment == 'production':
    from .production import defaults
elif environment == 'development':
    from .develop import defaults

# Setup normal rotating log handler
make_dirs()
rotate = RotatingFileHandler(os.path.join(Settings.get('client/logs/path'), 'forever.log'),
                             maxBytes=int(Settings.get('client/logs/max_size')),
                             backupCount=1)
rotate.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))

buffering_handler = MemoryHandler(int(Settings.get('client/logs/buffer_size')), target=rotate)

logging.getLogger().addHandler(buffering_handler)
logging.getLogger().setLevel(Settings.get('client/logs/level', type=int))

if environment == 'development':
    # Setup logging output to console
    devh = logging.StreamHandler()
    devh.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))
    logging.getLogger().addHandler(devh)
    logging.getLogger().setLevel(logging.INFO)

logging.getLogger().info("FAF version: {} Environment: {}".format(version.get_git_version(), environment))
