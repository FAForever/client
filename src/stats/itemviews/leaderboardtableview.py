from PyQt5 import QtCore, QtGui, QtWebEngineWidgets, QtWidgets

from .leaderboardheaderview import VerticalHeaderView
from .leaderboardtablemenu import LeaderboardTableMenu


class LeaderboardTableView(QtWidgets.QTableView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)
        self.setSelectionBehavior(self.SelectRows)
        self.setSelectionMode(self.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)

        self.setVerticalHeader(VerticalHeaderView())
        self.mHoverRow = -1

    def hoverIndex(self):
        return QtCore.QModelIndex(self.model().index(self.mHoverRow, 0))
    
    def updateHoverRow(self, event):
        index = self.indexAt(event.pos())
        oldHoverRow = self.mHoverRow
        self.mHoverRow = index.row()

        if self.selectionBehavior() == self.SelectRows and oldHoverRow != self.mHoverRow:
            if oldHoverRow != -1:
                for i in range(self.model().columnCount()):
                    self.update(self.model().index(oldHoverRow, i))
            if self.mHoverRow != -1:
                for i in range(self.model().columnCount()):
                    self.update(self.model().index(self.mHoverRow, i))

    def mouseMoveEvent(self, event):
        QtWidgets.QTableView.mouseMoveEvent(self, event)
        self.updateHoverRow(event)
        self.verticalHeader().updateHoverSection(event)
    
    def wheelEvent(self, event):
        QtWidgets.QTableView.wheelEvent(self, event)
        self.updateHoverRow(event)
        self.verticalHeader().updateHoverSection(event)
    
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            row = self.indexAt(event.pos()).row()
            if row != -1:
                name_index = self.model().index(row, 0)
                id_index = self.model().index(row, 8)
                name = self.model().data(name_index)
                uid = int(self.model().data(id_index))
                self.selectRow(row)
                self.contextMenu(event, name, uid)
        else:
            QtWidgets.QTableView.mousePressEvent(self, event)
        self.updateHoverRow(event)
        self.verticalHeader().updateHoverSection(event)

    def contextMenu(self, event, name, uid):
        client = self.parent().parent().client
        leaderboardName = self.parent().parent().leaderboardName
        menuHandler = LeaderboardTableMenu.build(self, client, leaderboardName)
        menu = menuHandler.getMenu(name, uid)
        menu.popup(QtGui.QCursor.pos())
