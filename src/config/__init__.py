from . import version

from collections import defaultdict

import os
import sys
import logging
import trueskill
from logging.handlers import RotatingFileHandler
from PyQt4 import QtCore

trueskill.setup(mu=1500, sigma=500, beta=250, tau=5, draw_probability=0.10)

_settings = QtCore.QSettings("ForgedAllianceForever", "FA Lobby")
_unpersisted_settings = defaultdict(dict)


class Settings:
    """
    This wraps QSettings, fetching default values from the
    selected configuration module if the key isn't found.
    """

    @staticmethod
    def persisted_property(key, default_value=None, is_bool=False, persist_if=lambda self: True, on_changed=None):
        """

        :param key: QSettings key to persist with
        :param default_value: default value
        :param is_bool: Persist booleans as strings, do conversion. Implies default_value=False
        :param persist_if: Lambda predicate that gets self as a first argument.
                           Determines whether or not to persist the value
        :return: a property suitable for a class
        """
        if is_bool:
            def get(self):
                if key in _unpersisted_settings[self]:
                    return _unpersisted_settings[self][key]
                return _settings.value(key) == "true"

            def set(self, val):
                _unpersisted_settings[self][key] = val
                if persist_if(self):
                    _settings.setValue(key, "true" if val else "false")
                else:
                    _settings.remove(key)
                if on_changed:
                    on_changed(self)
        else:
            def get(self):
                if key in _unpersisted_settings[self]:
                    return _unpersisted_settings[self][key]
                return _settings.value(key, default_value)

            def set(self, val):
                _unpersisted_settings[self][key] = val
                if persist_if(self):
                    _settings.setValue(key, val)
                else:
                    _settings.remove(key)
                if on_changed:
                    on_changed(self)
        return property(get, set, doc="Persisted property: {}".format(key))

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


VERSION = version.get_git_version()


def is_development_version():
    return version.is_development_version(VERSION)


# FIXME: Don't initialize proxy code that shows a dialogue box on import
no_dialogs = False

if os.getenv("FAF_FORCE_PRODUCTION") or getattr(sys, 'frozen', False) and not version.is_prerelease_version(VERSION):
    from production import defaults

    make_dirs()
    rotate = RotatingFileHandler(filename=os.path.join(Settings.get('DIR', 'LOG'), 'forever.log'),
                                 maxBytes=Settings.get('MAX_SIZE', 'LOG'),
                                 backupCount=10)
    rotate.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))
    logging.getLogger().addHandler(rotate)
    logging.getLogger().setLevel(Settings.get('LEVEL', 'LOG'))
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
    rotate = RotatingFileHandler(filename=os.path.join(Settings.get('DIR', 'LOG'), 'forever.log'),
                                 maxBytes=Settings.get('MAX_SIZE', 'LOG'),
                                 backupCount=10)
    rotate.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))
    logging.getLogger().addHandler(rotate)
    logging.getLogger().setLevel(Settings.get('LEVEL', 'LOG'))

logging.getLogger().info("FAF version: {}".format(version.get_git_version()))
