from PyQt5.QtCore import QObject, pyqtSignal


class ChatWidget(QObject):
    channel_quit_request = pyqtSignal(object)
    tab_changed = pyqtSignal(object)

    def __init__(self, theme):
        QObject.__init__(self)
        self._channels = {}
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
        self.base.currentChanged.connect(self._at_tab_changed)

    def add_channel(self, widget, key, index=None):
        if key in self._channels:
            return
        self._channels[key] = widget
        if index is None:
            self.base.addTab(widget.base, key.name)
        else:
            self.base.insertTab(index, widget.base, key.name)

    def remove_channel(self, key):
        widget = self._channels.pop(key, None)
        if widget is None:
            return
        self.base.removeTab(self.base.indexOf(widget.base))

    def write_server_message(self, msg):
        self.form.serverLogArea.appendPlainText(msg)

    def _at_tab_close_request(self, idx):
        self.channel_quit_request.emit(self.base.widget(idx).cid)

    def switch_to_channel(self, key):
        widget = self._channels.get(key, None)
        if widget is None:
            return
        self.base.setCurrentIndex(self.base.indexOf(widget.base))

    def set_tab_text(self, key, text):
        widget = self._channels.get(key, None)
        if widget is None:
            return
        idx = self.base.indexOf(widget.base)
        self.base.setTabText(idx, text)

    def _at_tab_changed(self, idx):
        if idx == -1:
            return
        for cid in self._channels:
            if idx == self.base.indexOf(self._channels[cid].base):
                self.tab_changed.emit(cid)
