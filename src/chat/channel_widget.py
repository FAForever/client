import util
from PyQt5 import QtGui

FormClass, BaseClass = util.THEME.loadUiType("chat/channel.ui")


class ChannelWidget(FormClass, BaseClass):
    def __init__(self):
        BaseClass.__init__(self)
        self.setupUi(self)

    def set_chatter_model(self, model):
        self.nickList.setModel(model)

    def set_chatter_delegate(self, delegate):
        self.nickList.setItemDelegate(delegate)

    def append_line(self, line):
        cursor = self.chatArea.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        self.chatArea.setTextCursor(cursor)
        self.chatArea.insertHtml("{}: {}<br>".format(line.sender, line.text))
