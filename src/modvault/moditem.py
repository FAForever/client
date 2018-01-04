from PyQt5 import QtCore, QtWidgets, QtGui
from downloadManager import IconCallback
import os
import util
import urllib.parse


class ModView(QtCore.QObject):
    """
    Helps with displaying mods in the mod widget. Handles updates to view
    unrelated to underlying data, like downloading mod previews. Forwards
    interaction with the view.
    """
    mod_double_clicked = QtCore.pyqtSignal(object)

    def __init__(self, model, view, delegate, dler):
        QtCore.QObject.__init__(self)
        self._model = model
        self._view = view
        self._delegate = delegate
        self._dler = dler

        self._view.setModel(self._model)
        self._view.setItemDelegate(self._delegate)
        self._delegate.mod_preview_missing.connect(self.download_mod_preview)
        self._view.doubleClicked.connect(self._mod_double_clicked)
        self._view.viewport().installEventFilter(self._delegate.tooltip_filter)

    def download_mod_preview(self, mod):
        name = os.path.basename(urllib.parse.unquote(mod.thumbnail))
        cb = IconCallback(name, self._mod_preview_downloaded)
        self._dler.downloadModPreview(mod.thumbnail, name, cb)  # (url, name, requester)

    # TODO make it a utility function?
    def _model_items(self):
        model = self._model
        for i in range(model.rowCount(QtCore.QModelIndex())):
            yield model.index(i, 0)

    def _mod_preview_downloaded(self, modname, icon):
        for idx in self._model_items():
            mod = idx.data().mod
            if mod.thumbnail != "":
                name = os.path.basename(urllib.parse.unquote(mod.thumbnail))
                if name.lower() == modname.lower():  # Previews are not case-preserving
                    self._view.update(idx)

    def _mod_double_clicked(self, idx):
        self.mod_double_clicked.emit(idx.data().mod)


class ModItemDelegate(QtWidgets.QStyledItemDelegate):
    mod_preview_missing = QtCore.pyqtSignal(object)
    painting = QtCore.pyqtSignal()

    ICON_RECT = 100
    ICON_CLIP_TOP_LEFT = 3
    ICON_CLIP_BOTTOM_RIGHT = -7
    ICON_SHADOW_OFFSET = 8
    SHADOW_COLOR = QtGui.QColor("#202020")
    FRAME_THICKNESS = 1
    FRAME_COLOR = QtGui.QColor("#303030")
    TEXT_OFFSET = 10
    TEXT_RIGHT_MARGIN = 5

    TEXT_WIDTH = 250
    ICON_SIZE = 110
    PADDING = 10

    def __init__(self, formatter):
        QtWidgets.QStyledItemDelegate.__init__(self)
        self._formatter = formatter
        self.tooltip_filter = ModTooltipFilter(self._formatter)

    def paint(self, painter, option, index):
        painter.save()

        data = index.data()
        text = self._formatter.text(data)
        icon = self._formatter.icon(data)

        self._check_mod_preview(data)

        self._draw_clear_option(painter, option)
        self._draw_icon_shadow(painter, option)
        self._draw_icon(painter, option, icon)
        self._draw_frame(painter, option)
        self._draw_text(painter, option, text)

        painter.restore()
        self.painting.emit()

    def _check_mod_preview(self, data):
        needed_preview = self._formatter.needed_mod_preview(data)  # mod or None
        if needed_preview:
            self.mod_preview_missing.emit(data.mod)

    @staticmethod
    def _draw_clear_option(painter, option):
        option.icon = QtGui.QIcon()
        option.text = ""
        option.widget.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem,
                                          option, painter, option.widget)

    def _draw_icon_shadow(self, painter, option):
        painter.fillRect(option.rect.left() + self.ICON_SHADOW_OFFSET,
                         option.rect.top() + self.ICON_SHADOW_OFFSET,
                         self.ICON_RECT, self.ICON_RECT, self.SHADOW_COLOR)

    def _draw_icon(self, painter, option, icon):
        rect = option.rect.adjusted(self.ICON_CLIP_TOP_LEFT, self.ICON_CLIP_TOP_LEFT,
                                    self.ICON_CLIP_BOTTOM_RIGHT, self.ICON_CLIP_BOTTOM_RIGHT)
        icon.paint(painter, rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

    def _draw_frame(self, painter, option):
        pen = QtGui.QPen()
        pen.setWidth(self.FRAME_THICKNESS)
        pen.setBrush(self.FRAME_COLOR)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawRect(option.rect.left() + self.ICON_CLIP_TOP_LEFT,
                         option.rect.top() + self.ICON_CLIP_TOP_LEFT,
                         self.ICON_RECT, self.ICON_RECT)

    def _draw_text(self, painter, option, text):
        left_off = self.ICON_RECT + self.TEXT_OFFSET
        top_off = 0  # self.TEXT_OFFSET
        right_off = self.TEXT_RIGHT_MARGIN
        bottom_off = 0
        painter.translate(option.rect.left() + left_off, option.rect.top() + top_off)
        clip = QtCore.QRectF(0, 0,
                             option.rect.width() - left_off - right_off,
                             option.rect.height() - top_off - bottom_off)
        html = QtGui.QTextDocument()
        html.setHtml(text)
        html.drawContents(painter, clip)

    def sizeHint(self, option, index):
        return QtCore.QSize(self.ICON_SIZE + self.TEXT_WIDTH + self.PADDING, self.ICON_SIZE)


class ModTooltipFilter(QtCore.QObject):
    def __init__(self, formatter):
        QtCore.QObject.__init__(self)
        self._formatter = formatter

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.ToolTip:
            return self._handle_tooltip(obj, event)
        else:
            return super().eventFilter(obj, event)

    def _handle_tooltip(self, widget, event):
        view = widget.parent()
        idx = view.indexAt(event.pos())
        if not idx.isValid():
            return False

        tooltip_text = self._formatter.tooltip(idx.data())
        QtWidgets.QToolTip.showText(event.globalPos(), tooltip_text, widget)
        return True


class ModItemFormatter:
    FORMATTER_MOD = str(util.THEME.readfile("modvault/modinfo.qthtml"))
    FORMATTER_MOD_UI = str(util.THEME.readfile("modvault/modinfoui.qthtml"))

    def __init__(self):
        return

    def text(self, data):
        mod = data.mod
        descr = mod.description if len(mod.description) < 175 else mod.description[:172] + "..."

        formatting = {
            "color": "limegreen" if mod.installed else "white",
            "version": mod.version,
            "title": mod.name,
            "description": descr,
            "author": mod.author,
            "downloads": mod.downloads,
            "played": mod.played,
            "likes": int(mod.likes),
            "date": QtCore.QDateTime.fromSecsSinceEpoch(mod.date, 0).toString("yyyy-MM-dd"),
            "modtype": "UI mod" if mod.is_uimod else ""
        }

        if mod.is_uimod:
            return self.FORMATTER_MOD_UI.format(**formatting)
        else:
            return self.FORMATTER_MOD.format(**formatting)

    @staticmethod
    def icon(data):
        return data.mod_icon

    @staticmethod
    def needed_mod_preview(data):
        return data.mod_icon is None

    @staticmethod
    def tooltip(data):
        return '<p width="230">{}</p>'.format(data.mod.description)


class ModViewBuilder:
    def __init__(self, preview_dler):
        self._preview_dler = preview_dler

    def __call__(self, model, view):
        mod_formatter = ModItemFormatter()
        mod_delegate = ModItemDelegate(mod_formatter)
        modview = ModView(model, view, mod_delegate, self._preview_dler)
        return modview
