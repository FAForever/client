__author__ = 'Sheeo'

import version
import logging


def get_logger(name):
    logger = logging.getLogger(name)
    if "LOG_LEVEL_"+name in globals():
        logger.setLevel(globals()["LOG_LEVEL_"+name])
    return logger

if version.is_development_version():
    get_logger('config').info("Loading development configuration")
