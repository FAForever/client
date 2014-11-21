__author__ = 'Sheeo'

import version
import logging
import util  # Temporary, util is deprecated


class Settings(object):
    @staticmethod
    def get(key, group=None):
        value = None
        if group is None:
            value = util.settings.value(key)
        else:
            util.settings.beginGroup(group)
            value = util.settings.value(key)
            util.settings.endGroup()
        return value

    @staticmethod
    def set(key, value, group=None):
        if group is None:
            util.settings.setValue(key, value)
        else:
            util.settings.beginGroup(group)
            util.settings.setValue(key, value)
            util.settings.endGroup()

DEFAULT_BIN_DIR = util.BIN_DIR
GLOBAL_LOG_LEVEL = Settings.get('log_level') or logging.WARNING


if version.is_development_version():
    GLOBAL_LOG_LEVEL = logging.INFO

    # Setup logging output
    devh = logging.StreamHandler()
    devh.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-40s %(message)s'))
    logging.getLogger().addHandler(devh)
    logging.getLogger().setLevel(GLOBAL_LOG_LEVEL)

    for k in []:
        logging.getLogger(k).setLevel(logging.DEBUG)

    logging.getLogger(__name__).info("Loading development configuration")
else:
    logging.basicConfig(filename=util.LOG_FILE_FAF, level=GLOBAL_LOG_LEVEL,
                        format='%(asctime)s %(levelname)-8s %(name)-40s %(message)s')

# Set default QSettings here
if Settings.get('bin_dir', 'fa') is None:
    Settings.set('bin_dir', util.BIN_DIR, 'fa')
