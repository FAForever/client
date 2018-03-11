from PyQt5.QtCore import QObject, pyqtSignal


class ChatWidget(QObject):
    channel_quit_request = pyqtSignal(object)

    def __init__(self, theme):
        QObject.__init__(self)
        self._channels = set()
        self.set_theme(theme)

    @classmethod
    def build(cls, theme, **kwargs):
        return cls(theme)

    def set_theme(self, theme):
        formc, basec = theme.loadUiType("chat/chat.ui")
        self.form = formc()
        self.base = basec()
        self.form.setupUi(self.base)
        self.base.tabCloseRequested.connect(self._at_tab_close_request)

    def add_channel(self, channel, name, index=None):
        if channel in self._channels:
            return
        self._channels.add(channel)
        if index is None:
            self.base.addTab(channel.base, name)
        else:
            self.base.insertTab(index, channel.base, name)

    def remove_channel(self, channel):
        if channel not in self._channels:
            return
        self._channels.remove(channel)
        self.base.removeTab(self.base.indexOf(channel.base))

    def write_server_message(self, msg):
        self.form.serverLogArea.appendPlainText(msg)

    def _at_tab_close_request(self, idx):
        self.channel_quit_request.emit(self.base.widget(idx).cid)

    def switch_to_channel(self, channel):
        if channel not in self._channels:
            return
        self.base.setCurrentIndex(self.base.indexOf(channel.base))
