from PyQt5.QtWidgets import QListView
from PyQt5.QtCore import pyqtSignal


class ChatterListView(QListView):
    """
    Used to let chatter list delegate fit its width to list view's width.
    """
    resized = pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        QListView.__init__(self, *args, **kwargs)

    def resizeEvent(self, event):
        QListView.resizeEvent(self, event)
        self.resized.emit(self.maximumViewportSize())
        self.updateGeometries()
