from PyQt5 import QtCore, QtWidgets


class LeaderboardItemDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        opt = QtWidgets.QStyleOptionViewItem(option)
        opt.state &= ~QtWidgets.QStyle.State_HasFocus
        opt.state &= ~QtWidgets.QStyle.State_MouseOver

        view = opt.styleObject
        behavior = view.selectionBehavior()
        hoverIndex = view.hoverIndex()

        if not (option.state & QtWidgets.QStyle.State_Selected) and (behavior != QtWidgets.QTableView.SelectItems):
            if (behavior == QtWidgets.QTableView.SelectRows) and (hoverIndex.row() == index.row()):
                opt.state |= QtWidgets.QStyle.State_MouseOver
        
        self.initStyleOption(opt, index)
        painter.save()
        text = opt.text
        opt.text = ""
        opt.widget.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, opt, painter, opt.widget)
        if opt.state & QtWidgets.QStyle.State_Selected:
            painter.setPen(QtCore.Qt.white)
        if index.column() == 0:
            rect = QtCore.QRect(opt.rect)
            rect.setLeft(opt.rect.left() + opt.rect.width()//2.125)
            painter.drawText(rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, text)
        else:
            painter.drawText(opt.rect, QtCore.Qt.AlignCenter, text)
        painter.restore()
