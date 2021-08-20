from enum import Enum

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication, QTabBar

from model.chat.channel import PARTY_CHANNEL_SUFFIX, ChannelType


class TabIcon(Enum):
    IDLE = "idle"
    NEW_MESSAGE = "new_message"
    BLINK_ACTIVE = "blink_active"
    BLINK_INACTIVE = "blink_inactive"


class ChatWidget(QObject):
    channel_quit_request = pyqtSignal(object)
    tab_changed = pyqtSignal(object)

    def __init__(self, theme):
        QObject.__init__(self)
        self._channels = {}
        self._theme = theme
        self.set_theme()

    @classmethod
    def build(cls, theme, **kwargs):
        return cls(theme)

    def set_theme(self):
        formc, basec = self._theme.loadUiType("chat/chat.ui")
        self.form = formc()
        self.base = basec()
        self.form.setupUi(self.base)
        self.base.tabCloseRequested.connect(self._at_tab_close_request)
        self.base.currentChanged.connect(self._at_tab_changed)
        self.remove_server_tab_close_button()

    def remove_server_tab_close_button(self):
        self.base.tabBar().setTabButton(0, QTabBar.RightSide, None)

    def add_channel(self, widget, key, index=None):
        if key in self._channels:
            return
        self._channels[key] = widget
        if index is None:
            self._add_tab_in_default_spot(widget, key)
        else:
            self.base.insertTab(index, widget.base, key.name)
        self.set_tab_icon(key, TabIcon.IDLE)

    def _add_tab_in_default_spot(self, widget, key):
        if key.name.endswith(PARTY_CHANNEL_SUFFIX):
            tab_name = "Party Channel"
        else:
            tab_name = key.name
        if key.type == ChannelType.PRIVATE:
            self.base.addTab(widget.base, tab_name)
            return
        try:
            last_public_tab = max([
                self.base.indexOf(w.base)
                for cid, w in self._channels.items()
                if cid.type == ChannelType.PUBLIC and cid != key
            ])
            self.base.insertTab(last_public_tab + 1, widget.base, tab_name)
            return
        except ValueError:
            pass
        try:
            first_private_tab = min([
                self.base.indexOf(w.base)
                for cid, w in self._channels.items()
                if cid.type == ChannelType.PRIVATE and cid != key
            ])
            self.base.insertTab(first_private_tab, widget.base, tab_name)
            return
        except ValueError:
            pass
        self.base.addTab(widget.base, tab_name)

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

    def set_tab_icon(self, key, name):
        icon = self._theme.icon("chat/tabicon/{}.png".format(name.value))
        widget = self._channels.get(key, None)
        if widget is None:
            return
        idx = self.base.indexOf(widget.base)
        self.base.setTabIcon(idx, icon)

    def alert_tab(self):
        QApplication.alert(self.base)

    def _index_to_cid(self, idx):
        for cid in self._channels:
            if idx == self.base.indexOf(self._channels[cid].base):
                return cid
        return None

    def _at_tab_changed(self, idx):
        cid = self._index_to_cid(idx)
        if cid is None:
            return
        self.tab_changed.emit(cid)

    def current_channel(self):
        current_idx = self.base.currentIndex()
        return self._index_to_cid(current_idx)
