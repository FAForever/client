import util

FormClass, BaseClass = util.THEME.loadUiType("chat/chat.ui")


class ChatWidget(FormClass, BaseClass):
    def __init__(self):
        BaseClass.__init__(self)
        self.setupUi(self)
        self._channels = set()

    def add_channel(self, channel, name, index=None):
        if channel in self._channels:
            return
        self._channels.add(channel)
        if index is None:
            self.addTab(channel, name)
        else:
            self.insertTab(index, channel, name)

    def remove_channel(self, channel):
        if channel not in self._channels:
            return
        self._channels.remove(channel)
        self.removeTab(self.indexOf(channel))

    def write_server_message(self, msg):
        self.serverLogArea.appendPlainText(msg)
