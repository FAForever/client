import logging


def with_logger[T](cls: type[T]) -> type[T]:
    attr_name = '_logger'
    cls_name = cls.__name__
    module = cls.__module__
    assert module is not None
    cls_name = module + '.' + cls_name
    setattr(cls, attr_name, logging.getLogger(cls_name))
    return cls
