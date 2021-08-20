import faulthandler
import locale
import logging
import os
import sys
import traceback
from logging.handlers import MemoryHandler, RotatingFileHandler

from PyQt5 import QtCore

import fafpath

from . import version
from .develop import default_values as develop_defaults
from .production import default_values as production_defaults
from .testing import default_values as testing_defaults

if sys.platform == 'win32':
    import ctypes

    import win32api
    import win32con
    import win32security

    from . import admin

_settings = QtCore.QSettings(
    QtCore.QSettings.IniFormat,
    QtCore.QSettings.UserScope,
    "ForgedAllianceForever",
    "FA Lobby",
)
_unpersisted_settings = {}

CONFIG_PATH = os.path.dirname(_settings.fileName())
UNITDB_CONFIG_FILE = os.path.join(CONFIG_PATH, "unitdb.conf")


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
    def persisted_property(
        key,
        default_value=None,
        persist_if=lambda self: True,
        type=str,
    ):
        """
        Create a magically persisted property

        :param key: QSettings key to persist with
        :param default_value: default value
        :param persist_if: Lambda predicate that gets self as a first argument.
                           Determines whether or not to persist the value
        :param type: Type of values for persisting
        :return: a property suitable for a class
        """
        return property(
            lambda s: Settings.get(key, default=default_value, type=type),
            lambda s, v: Settings.set(key, v, persist=persist_if(s)),
            doc='Persisted property: {}. Default: {}'.format(
                key, default_value,
            ),
        )

    @staticmethod
    def sync():
        _settings.sync()

    @staticmethod
    def fileName():
        return _settings.fileName()

    @staticmethod
    def contains(key):
        return key in _unpersisted_settings or _settings.contains(key)


def set_data_path_permissions():
    """
    Set the owner of C:\\ProgramData\\FAForever recursively to the current user
    """
    if not admin.isUserAdmin():
        win32api.MessageBox(
            0,
            (
                "FA Forever needs to fix folder permissions due to user "
                "change. Please confirm the following two admin prompts."
            ),
            "User changed",
        )
    if sys.platform == 'win32' and ('CI' not in os.environ):
        data_path = Settings.get('client/data_path')
        if os.path.exists(data_path):
            my_user = win32api.GetUserNameEx(win32con.NameSamCompatible)
            admin.runAsAdmin(["icacls", data_path, "/setowner", my_user, "/T"])
            admin.runAsAdmin(["icacls", data_path, "/reset", "/T"])


def check_data_path_permissions():
    """
    Checks if the current user is owner of C:\\ProgramData\\FAForever
    Fixes the permissions in case that FAF was run as different user before
    """
    if sys.platform == 'win32' and ('CI' not in os.environ):
        data_path = Settings.get('client/data_path')
        if os.path.exists(data_path):
            try:
                my_user = win32api.GetUserNameEx(win32con.NameSamCompatible)
                sd = win32security.GetFileSecurity(
                    data_path, win32security.OWNER_SECURITY_INFORMATION,
                )
                owner_sid = sd.GetSecurityDescriptorOwner()
                name, domain, type = win32security.LookupAccountSid(
                    None, owner_sid,
                )
                data_path_owner = "{}\\{}".format(domain, name)

                if my_user != data_path_owner:
                    set_data_path_permissions()
            except BaseException as e:
                # we encountered error 1332 in win32security.LookupAccountSid
                # here: http://forums.faforever.com/viewtopic.php?f=3&t=13728
                # msdn.microsoft.com/en-us/library/windows/desktop/aa379166.aspx
                # states:
                # "It also occurs for SIDs that have no corresponding account
                # name, such as a logon SID that identifies a logon session."
                # so let's just fix permissions on every exception for now and
                # wait for someone stuck in a permission-loop
                win32api.MessageBox(
                    0,
                    "FA Forever ran into an exception "
                    "checking the data folder permissions: '{}'\n"
                    "If you get this popup more than one time, please report "
                    "a screenshot of this popup to tech support forum. "
                    "Full stacktrace:\n{}".format(e, traceback.format_exc()),
                    "Permission check exception",
                )
                set_data_path_permissions()


def make_dirs():
    check_data_path_permissions()
    for dir_ in [
        'client/data_path',
        'game/logs/path',
        'game/bin/path',
        'game/mods/path',
        'game/engine/path',
        'game/maps/path',
    ]:
        path = Settings.get(dir_)
        if path is None:
            raise Exception("Missing configured path for {}".format(dir_))
        if not os.path.isdir(path):
            try:
                os.makedirs(path)
            except IOError:
                set_data_path_permissions()
                os.makedirs(path)


VERSION = version.get_release_version(
    dir=fafpath.get_resdir(),
    git_dir=fafpath.get_srcdir(),
)


def is_development_version():
    return version.is_development_version(VERSION)


# FIXME: Don't initialize proxy code that shows a dialogue box on import
no_dialogs = False

environment = 'production'


def is_beta():
    return environment == 'development'

# TODO: move stuff below to Settings __init__ once we make it an actual object


if _settings.contains('client/force_environment'):
    environment = _settings.value('client/force_environment', 'development')

for defaults in [production_defaults, develop_defaults, testing_defaults]:
    for key, value in defaults.items():
        if isinstance(value, str):
            defaults[key] = value.format(host=Settings.get('host'))

if environment == 'production':
    defaults = production_defaults
elif environment == 'development':
    defaults = develop_defaults
elif environment == 'test':
    defaults = testing_defaults


def os_language():
    # locale is unreliable on Windows
    if sys.platform == 'win32':
        windll = ctypes.windll.kernel32
        locale_code = windll.GetUserDefaultUILanguage()
        os_locale = locale.windows_locale.get(locale_code, None)
    else:
        os_locale = locale.getlocale()[0]

    # sanity checks
    if os_locale is None:
        return None
    if len(os_locale) < 2:
        return None
    country = os_locale[:2].lower()
    if not country.isalpha():
        return None
    return country


if not Settings.contains('client/language'):
    Settings.set('client/language', os_language())


# Setup normal rotating log handler
make_dirs()


def setup_file_handler(filename):
    # check permissions of writing the log file first
    # (which fails when changing users)
    log_file = os.path.join(Settings.get('client/logs/path'), filename)
    try:
        with open(log_file, "a"):
            pass
    except IOError:
        set_data_path_permissions()
    rotate = RotatingFileHandler(
        os.path.join(Settings.get('client/logs/path'), filename),
        maxBytes=int(Settings.get('client/logs/max_size')),
        backupCount=1,
    )
    rotate.setFormatter(
        logging.Formatter(
            '%(asctime)s %(levelname)-8s %(name)-30s %(message)s',
        ),
    )
    return MemoryHandler(
        int(Settings.get('client/logs/buffer_size')),
        target=rotate,
    )


client_handler = setup_file_handler('forever.log')

logging.getLogger().addHandler(client_handler)
logging.getLogger().setLevel(Settings.get('client/logs/level', type=int))

if Settings.get('client/logs/console', False, type=bool):
    # Setup logging output to console
    devh = logging.StreamHandler()
    devh.setFormatter(
        logging.Formatter(
            '%(asctime)s %(levelname)-8s %(name)-30s %(message)s',
        ),
    )
    logging.getLogger().addHandler(devh)
    logging.getLogger().setLevel(Settings.get('client/logs/level', type=int))

logging.getLogger().info(
    "FAF version: {} Environment: {}".format(VERSION, environment),
)


def qt_log_handler(type_, context, text):
    loglvl = None
    if type_ == QtCore.QtDebugMsg:
        loglvl = logging.DEBUG
    elif type_ == QtCore.QtInfoMsg:
        loglvl = logging.INFO
    elif type_ == QtCore.QtWarningMsg:
        loglvl = logging.WARNING
    elif type_ == QtCore.QtCriticalMsg:
        loglvl = logging.ERROR
    elif type_ == QtCore.QtFatalMsg:
        loglvl = logging.CRITICAL
    if loglvl is None:
        return
    logging.getLogger().log(loglvl, "Qt: " + text)


QtCore.qInstallMessageHandler(qt_log_handler)

fault_handler_file = None


def setup_fault_handler():
    global fault_handler_file
    log_path = os.path.join(Settings.get('client/logs/path'), 'crash.log')
    try:
        max_sz = int(Settings.get('client/logs/max_size'))
        rotate = RotatingFileHandler(
            log_path,
            maxBytes=max_sz,
            backupCount=1,
        )
        # Rollover does it unconditionally, not looking at max size,
        # so we need to check it manually
        try:
            finfo = os.stat(log_path)
            if finfo.st_size > max_sz:
                rotate.doRollover()
        except FileNotFoundError:
            pass
        rotate.close()

        # This file must be kept open so that faulthandler can write to the
        # same file descriptor no matter the circumstances
        fault_handler_file = open(log_path, 'a')
    except IOError as e:
        logging.getLogger().error(
            'Failed to setup crash.log for the fault handler: ' + e.strerror,
        )
        return

    faulthandler.enable(fault_handler_file)


setup_fault_handler()


def clear_logging_handlers():
    global fault_handler_file
    QtCore.qInstallMessageHandler(None)
    faulthandler.disable()
    fault_handler_file.close()
