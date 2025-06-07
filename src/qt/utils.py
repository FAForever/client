import types
from collections.abc import Generator
from contextlib import contextmanager

from PyQt6.QtCore import QFile
from PyQt6.QtCore import QObject
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QWidget


def monkeypatch_method(obj, name, fn):
    old_fn = getattr(obj, name)

    def wrapper(self, *args, **kwargs):
        return fn(self, old_fn, *args, **kwargs)
    setattr(obj, name, types.MethodType(wrapper, obj))


@contextmanager
def qopen(path: str, flags: QFile.OpenModeFlag) -> Generator[QFile, None, None]:
    file = QFile(path)
    try:
        file.open(flags)
        yield file
    finally:
        file.close()


@contextmanager
def qpainter(painter: QPainter) -> Generator[QPainter, None, None]:
    try:
        painter.save()
        yield painter
    finally:
        painter.restore()


@contextmanager
def block_signals[T: QObject](obj: T, /) -> Generator[T]:
    try:
        obj.blockSignals(True)
        yield obj
    finally:
        obj.blockSignals(False)


def center_widget_on_screen(widget: QWidget) -> None:
    rect = widget.rect()
    screen = widget.screen()
    assert screen is not None
    rect.moveCenter(screen.availableGeometry().center())
    widget.move(rect.topLeft())
