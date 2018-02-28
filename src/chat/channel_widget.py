import util
from PyQt5 import QtGui
from PyQt5.QtCore import pyqtSignal
import re


FormClass, BaseClass = util.THEME.loadUiType("chat/channel.ui")


class ChannelWidget(FormClass, BaseClass):
    line_typed = pyqtSignal(str)
    chatter_list_resized = pyqtSignal(object)

    def __init__(self, cid):
        BaseClass.__init__(self)
        self.setupUi(self)
        self.chatEdit.returnPressed.connect(self._at_line_typed)
        self.nickList.resized.connect(self.chatter_list_resized.emit)
        self.cid = cid

    def set_chatter_model(self, model):
        self.nickList.setModel(model)

    def set_chatter_delegate(self, delegate):
        self.nickList.setItemDelegate(delegate)

    def set_chatter_tooltips(self, tooltip_filter):
        self.nickList.viewport().installEventFilter(tooltip_filter)

    def append_line(self, line):
        cursor = self.chatArea.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        self.chatArea.setTextCursor(cursor)
        self.chatArea.insertHtml("{}: {}<br>".format(line.sender, line.text))

    def set_autocompletion_source(self, channel):
        self.chatEdit.set_channel(channel)

    def _at_line_typed(self):
        text = self.chatEdit.text()
        self.chatEdit.clear()
        fragments = text.split("\n")
        for line in fragments:
            # Compound wacky Whitespace
            line = re.sub('\s', ' ', text).strip()
            if not line:
                continue
            self.line_typed.emit(line)
