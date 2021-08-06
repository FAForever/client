from PyQt5 import QtCore, QtGui, QtWebEngineWidgets, QtWidgets


class VerticalHeaderView(QtWidgets.QHeaderView):
    def __init__(self, *args, **kwargs):
        super().__init__(QtCore.Qt.Vertical, *args, **kwargs)
        self.setHighlightSections(True)
        self.setSectionResizeMode(self.Fixed)
        self.setVisible(True)
        self.setSectionsClickable(True)
        self.setAlternatingRowColors(True)
        self.setObjectName("VerticalHeader")

        self.hover = -1
        
    def paintSection(self, painter, rect, index):
        opt = QtWidgets.QStyleOptionHeader()
        self.initStyleOption(opt)
        opt.rect = rect
        opt.section = index
        opt.text = str(self.model().headerData(index, self.orientation(), QtCore.Qt.DisplayRole))
        opt.textAlignment = QtCore.Qt.AlignCenter

        state = QtWidgets.QStyle.State_None

        if self.highlightSections():
            if self.selectionModel().rowIntersectsSelection(index, QtCore.QModelIndex()):
                state |= QtWidgets.QStyle.State_On
            elif index == self.hover:
                state |= QtWidgets.QStyle.State_MouseOver

        opt.state |= state
        
        self.style().drawControl(QtWidgets.QStyle.CE_Header, opt, painter, self)
    
    def mouseMoveEvent(self, event):
        QtWidgets.QHeaderView.mouseMoveEvent(self, event)
        self.parent().updateHoverRow(event)
        self.updateHoverSection(event)
    
    def wheelEvent(self, event):
        QtWidgets.QHeaderView.wheelEvent(self, event)
        self.parent().updateHoverRow(event)
        self.updateHoverSection(event)
    
    def mousePressEvent(self, event):
        QtWidgets.QHeaderView.mousePressEvent(self, event)
        self.parent().updateHoverRow(event)
        self.updateHoverSection(event)

    def updateHoverSection(self, event):
        index = self.logicalIndexAt(event.pos())
        oldHover = self.hover
        self.hover = index

        if self.hover != oldHover:
            if oldHover != -1:
                self.updateSection(oldHover)
            if self.hover != -1:
                self.updateSection(self.hover)
