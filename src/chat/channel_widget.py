import logging
import re

from PyQt5.QtCore import QObject, Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QTextCursor, QTextDocument

from util.qt import monkeypatch_method

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
        self._override_widget_methods()
        self._load_css()
        self._sticky_scroll = ChatAreaStickyScroll(
            self.chat_area.verticalScrollBar(),
        )

    def _override_widget_methods(self):

        def on_key_release(obj, old_fn, keyevent):
            if keyevent.key() == 67:    # Ctrl-C
                self.chat_area.copy()
            else:
                old_fn(keyevent)
        monkeypatch_method(self.base, "keyReleaseEvent", on_key_release)

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
            line = re.sub(r'\s', ' ', line).strip()
            if not line:
                continue
            self.line_typed.emit(line)

    def show_chatter_list(self, should_show):
        self.nick_frame.setVisible(should_show)

    def append_line(self, text):
        # QTextEdit has its own ideas about scrolling and does not stay
        # in place when adding content
        self._sticky_scroll.save_scroll()

        cursor = self.chat_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_area.setTextCursor(cursor)
        self.chat_area.insertHtml(text)

        self._sticky_scroll.restore_scroll()

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
        return not self.base.isVisible()

    def set_topic(self, topic):
        self.announce_line.setText(topic)


class ChatAreaStickyScroll:
    def __init__(self, scrollbar):
        self._scrollbar = scrollbar
        self._scrollbar.valueChanged.connect(self._track_maximum)
        self._scrollbar.rangeChanged.connect(self._stick_at_range_changed)
        self._is_set_to_maximum = True
        self._old_value = self._scrollbar.value()
        self._saved_scroll = 0

    def save_scroll(self):
        self._saved_scroll = self._scrollbar.value()

    def restore_scroll(self):
        if self._is_set_to_maximum:
            self._scrollbar.setValue(self._scrollbar.maximum())
        else:
            self._scrollbar.setValue(self._saved_scroll)

    def _track_maximum(self, val):
        self._is_set_to_maximum = val == self._scrollbar.maximum()
        self._old_value = val

    def _stick_at_range_changed(self, min_, max_):
        if self._is_set_to_maximum:
            self._scrollbar.setValue(max_)
        else:
            self._scrollbar.setValue(self._old_value)
