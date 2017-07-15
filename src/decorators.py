import logging
from config import Settings


def with_logger(cls):
    attr_name = '_logger'
    cls_name = cls.__name__
    module = cls.__module__
    assert module is not None
    logger_name = module + '.' + cls_name
    logger = logging.getLogger(logger_name)
    loglevel = Settings.get('client/logs/' + module, default=logging.INFO, type=int)
    logger.setLevel(loglevel)
    setattr(cls, attr_name, logger)
    return cls
