from PyQt5.QtCore import QObject, pyqtSignal, QUrl, Qt
from PyQt5.QtGui import QTextDocument, QTextCursor
import re

import logging
logger = logging.getLogger(__name__)


class ChannelWidget(QObject):
    line_typed = pyqtSignal(str)
    chatter_list_resized = pyqtSignal(object)
    url_clicked = pyqtSignal(QUrl)
    css_reloaded = pyqtSignal()

    def __init__(self, channel, chat_area_css, theme, chat_config):
        QObject.__init__(self)
        self.channel = channel
        self._chat_area_css = chat_area_css
        self._chat_area_css.changed.connect(self._reload_css)
        self._chat_config = chat_config
        self._saved_scroll = None
        self.set_theme(theme)

    @classmethod
    def build(cls, channel, chat_area_css, theme, chat_config, **kwargs):
        return cls(channel, chat_area_css, theme, chat_config)

    @property
    def chat_area(self):
        return self.form.chatArea

    @property
    def chat_edit(self):
        return self.form.chatEdit

    @property
    def nick_frame(self):
        return self.form.nickFrame

    @property
    def nick_list(self):
        return self.form.nickList

    @property
    def nick_filter(self):
        return self.form.nickFilter

    @property
    def announce_line(self):
        return self.form.announceLine

    def set_theme(self, theme):
        formc, basec = theme.loadUiType("chat/channel.ui")
        self.form = formc()
        self.base = basec()
        self.form.setupUi(self.base)

        # Used by chat widget so it knows it corresponds to this widget
        self.base.cid = self.channel.id_key
        self.chat_edit.returnPressed.connect(self._at_line_typed)
        self.nick_list.resized.connect(self._chatter_list_resized)
        self.chat_edit.set_channel(self.channel)
        self.nick_filter.textChanged.connect(self._set_chatter_filter)
        self.chat_area.anchorClicked.connect(self._url_clicked)
        self._load_css()

    def _chatter_list_resized(self, size):
        self.chatter_list_resized.emit(size)

    def _url_clicked(self, url):
        self.url_clicked.emit(url)

    # This might be fairly expensive, as we reapply all chat lines to the area.
    # Make sure it's not called really often!
    def _reload_css(self):
        logger.info("Reloading chat CSS...")
        self._load_css()
        self.css_reloaded.emit()    # Qt does not reapply css on its own

    def _load_css(self):
        self.chat_area.document().setDefaultStyleSheet(self._chat_area_css.css)

    def clear_chat(self):
        self.chat_area.document().setHtml("")

    def add_avatar_resource(self, url, pix):
        doc = self.chat_area.document()
        link = QUrl(url)
        if not doc.resource(QTextDocument.ImageResource, link):
            doc.addResource(QTextDocument.ImageResource, link, pix)

    def _set_chatter_filter(self, text):
        self.nick_list.model().setFilterFixedString(text)

    def _at_line_typed(self):
        text = self.chat_edit.text()
        self.chat_edit.clear()
        fragments = text.split("\n")
        for line in fragments:
            # Compound wacky Whitespace
            line = re.sub('\s', ' ', text).strip()
            if not line:
                continue
            self.line_typed.emit(line)

    def show_chatter_list(self, should_show):
        self.nick_frame.setVisible(should_show)

    def append_line(self, text):
        self._save_scroll()
        cursor = self.chat_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_area.setTextCursor(cursor)
        self.chat_area.insertHtml(text)
        self._scroll_to_bottom_if_needed()

    def remove_lines(self, number):
        cursor = self.chat_area.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, number)
        cursor.removeSelectedText()

    def set_chatter_delegate(self, delegate):
        self.nick_list.setItemDelegate(delegate)

    def set_chatter_model(self, model):
        self.nick_list.setModel(model)
        model.setFilterCaseSensitivity(Qt.CaseInsensitive)

    def set_chatter_event_filter(self, event_filter):
        self.nick_list.viewport().installEventFilter(event_filter)

    def set_nick_edit_label(self, text):
        self.nick_filter.setPlaceholderText(text)

    @property
    def hidden(self):
        return self.base.isHidden()

    def _save_scroll(self):
        scrollbar = self.chat_area.verticalScrollBar()
        self._saved_scroll = scrollbar.value()

    def _scroll_to_bottom_if_needed(self):
        if self._saved_scroll is None:
            return
        scrollbar = self.chat_area.verticalScrollBar()
        max_scroll = scrollbar.maximum()
        snap_distance = self._chat_config.chat_scroll_snap_distance
        if max_scroll < self._saved_scroll + snap_distance:
            scrollbar.setValue(max_scroll)
        else:
            scrollbar.setValue(self._saved_scroll)
        self._saved_scroll = None

    def set_topic(self, topic):
        self.announce_line.setText(topic)
