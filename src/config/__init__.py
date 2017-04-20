from . import version
import os
import sys
import logging
import trueskill
import fafpath
import traceback
from PyQt4 import QtCore
from logging.handlers import RotatingFileHandler, MemoryHandler

if sys.platform == 'win32':
    import win32api
    import win32con
    import win32security
    from . import admin

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

def set_data_path_permissions():
    """
    Set the owner of C:\ProgramData\FAForever recursively to the current user
    """
    if not admin.isUserAdmin():
        win32api.MessageBox(0, "FA Forever needs to fix folder permissions due to user change. Please confirm the following two admin prompts.", "User changed")
    if sys.platform == 'win32' and (not 'CI' in os.environ):
        data_path = Settings.get('client/data_path')
        if os.path.exists(data_path):
            my_user = win32api.GetUserNameEx(win32con.NameSamCompatible)
            admin.runAsAdmin(["icacls", data_path, "/setowner", my_user, "/T"])
            admin.runAsAdmin(["icacls", data_path, "/reset", "/T"])

def check_data_path_permissions():
    """
    Checks if the current user is owner of C:\ProgramData\FAForever
    Fixes the permissions in case that FAF was run as different user before
    """
    if sys.platform == 'win32' and (not 'CI' in os.environ):
        data_path = Settings.get('client/data_path')
        if os.path.exists(data_path):
            try:
                my_user = win32api.GetUserNameEx(win32con.NameSamCompatible)
                sd = win32security.GetFileSecurity(data_path, win32security.OWNER_SECURITY_INFORMATION)
                owner_sid = sd.GetSecurityDescriptorOwner()
                name, domain, type = win32security.LookupAccountSid(None, owner_sid)
                data_path_owner = "%s\\%s" % (domain, name)

                if (my_user != data_path_owner):
                    set_data_path_permissions()
            except Exception as e:
                # we encountered error 1332 in win32security.LookupAccountSid here: http://forums.faforever.com/viewtopic.php?f=3&t=13728
                # https://msdn.microsoft.com/en-us/library/windows/desktop/aa379166(v=vs.85).aspx states:
                # "It also occurs for SIDs that have no corresponding account name, such as a logon SID that identifies a logon session."
                # so let's just fix permissions on every exception for now and wait for someone stuck in a permission-loop
                win32api.MessageBox(0,
                                    "FA Forever ran into an exception checking the data folder permissions: '{}'\n"
                                    "If you get this popup more than one time, please report a screenshot of this popup to tech support forum. "
                                    "Full stacktrace:\n{}".format(e, traceback.format_exc()),
                                    "Permission check exception")
                set_data_path_permissions()

def make_dirs():
    check_data_path_permissions()
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
            try:
                os.makedirs(path)
            except IOError as e:
                set_data_path_permissions()
                os.makedirs(path)

VERSION = version.get_release_version(fafpath.get_resdir())

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

for k, v in defaults.items():
    if isinstance(v, str):
        defaults[k] = v.format(host = Settings.get('host'))

# Setup normal rotating log handler
make_dirs()
#check permissions of writing the log file first (which fails when changing users)
log_file = os.path.join(Settings.get('client/logs/path'), 'forever.log')
try:
    with open(log_file, "a") as f:
        pass
except IOError as e:
    set_data_path_permissions()
rotate = RotatingFileHandler(os.path.join(Settings.get('client/logs/path'), 'forever.log'),
                             maxBytes=int(Settings.get('client/logs/max_size')),
                             backupCount=1)
rotate.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))

buffering_handler = MemoryHandler(int(Settings.get('client/logs/buffer_size')), target=rotate)

logging.getLogger().addHandler(buffering_handler)
logging.getLogger().setLevel(Settings.get('client/logs/level', type=int))

if Settings.get('client/logs/console', False, type=bool):
    # Setup logging output to console
    devh = logging.StreamHandler()
    devh.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))
    logging.getLogger().addHandler(devh)
    logging.getLogger().setLevel(Settings.get('client/logs/level', type=int))

logging.getLogger().info("FAF version: {} Environment: {}".format(VERSION, environment))
