import os
import logging
from logging.handlers import RotatingFileHandler, MemoryHandler

from config import dirs
from config import Settings
from config import VERSION, environment

def setup_logging():
    log_file = os.path.join(Settings.get("client/logs/path"), 'forever.log')
    try:
        with open(log_file, "a") as _:
            pass
    except IOError:
        dirs.set_data_path_permissions()
    rotate = RotatingFileHandler(os.path.join(Settings.get("client/logs/path"), 'forever.log'),
                                 maxBytes=Settings.get("client/logs/max_size"),
                                 backupCount=1)
    rotate.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))

    buffering_handler = MemoryHandler(Settings.get("client/logs/buffer_size"), target=rotate)

    logging.getLogger().addHandler(buffering_handler)
    logging.getLogger().setLevel(Settings.get("client/logs/level"))

    if environment == 'development':
        # Setup logging output to console
        devh = logging.StreamHandler()
        devh.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))
        logging.getLogger().addHandler(devh)
        logging.getLogger().setLevel(Settings.get("client/logs/level"))

    logging.getLogger().info(
            "FAF version: {} Environment: {}".format(VERSION, environment))
