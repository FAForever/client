import os
import logging
from logging.handlers import RotatingFileHandler, MemoryHandler

from config import dirs
from config import modules as cfg
from config import VERSION, environment

def setup_logging():
    log_file = os.path.join(cfg.game.logs_path.get(), 'forever.log')
    try:
        with open(log_file, "a") as _:
            pass
    except IOError:
        dirs.set_data_path_permissions()
    rotate = RotatingFileHandler(os.path.join(cfg.game.logs_path.get(), 'forever.log'),
                                 maxBytes=cfg.client.logs_max_size.get(),
                                 backupCount=1)
    rotate.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))

    buffering_handler = MemoryHandler(cfg.client.logs_buffer_size.get(), target=rotate)

    logging.getLogger().addHandler(buffering_handler)
    logging.getLogger().setLevel(cfg.client.logs_level.get())

    if environment == 'development':
        # Setup logging output to console
        devh = logging.StreamHandler()
        devh.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-30s %(message)s'))
        logging.getLogger().addHandler(devh)
        logging.getLogger().setLevel(cfg.client.logs_level.get())

    logging.getLogger().info(
            "FAF version: {} Environment: {}".format(VERSION, environment))
