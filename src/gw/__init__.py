from PyQt4 import QtGui, QtCore

class GalacticWar(QtCore.QObject):
    def __init__(self, client, *args, **kwargs):
        QtCore.QObject.__init__(self, *args, **kwargs)
        self.ui = QtGui.QGraphicsView()
        self.ui.setAutoFillBackground(False)
        self.client = client
        self.client.galacticTab.layout().addWidget(self.ui)
        