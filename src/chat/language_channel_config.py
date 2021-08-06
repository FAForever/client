from PyQt5.QtCore import QAbstractListModel, Qt

from chat.lang import LANGUAGE_CHANNELS


class ChannelEntry:
    def __init__(self, name, icon, checked):
        self.name = name
        self.icon = icon
        self.checked = checked


class LanguageChannelConfig:
    def __init__(self, parent_widget, settings, theme):
        self._parent_widget = parent_widget
        self._settings = settings
        self._theme = theme
        self._base = None
        self._form = None
        self._model = None
        self._setup_widget()
        self._setup_model()

    def _setup_widget(self):
        formc, basec = self._theme.loadUiType(
            "chat/language_channel_config.ui")
        self._form = formc()
        self._base = basec(self._parent_widget)
        self._form.setupUi(self._base)
        self._form.endDialogBox.accepted.connect(self._on_accepted)
        self._form.endDialogBox.rejected.connect(self._on_rejected)

    def _setup_model(self):
        self._model = CheckableStringListModel()
        self._form.channelListView.setModel(self._model)

    def _load_data(self):
        self._model.load_data(self._chan_flag_list())

    def _chan_flag_list(self):
        checked_channels = self._current_channels()
        channels = []
        for name, langs in LANGUAGE_CHANNELS.items():
            icon = self._country_icon(langs[0])
            checked = name in checked_channels
            channels.append(ChannelEntry(name, icon, checked))

        channels.sort(key=lambda x: x.name)
        return channels

    # TODO - move somewhere
    def _country_icon(self, country):
        return self._theme.icon("chat/countries/{}.png".format(country))

    def _current_channels(self):
        checked_channels = self._settings.get('client/lang_channels', "")
        return [c for c in checked_channels.split(';') if c]

    def _save_channels(self):
        channels = self._model.checked_channels()
        self._settings.set('client/lang_channels', ';'.join(channels))

    def _on_accepted(self):
        self._save_channels()
        self._base.accept()

    def _on_rejected(self):
        self._base.reject()

    def run(self):
        self._load_data()
        self._base.show()


class CheckableStringListModel(QAbstractListModel):
    def __init__(self):
        QAbstractListModel.__init__(self)
        self._items = []

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index, role=Qt.DisplayRole):
        item = self._index_item(index)
        if item is None:
            return None
        if role == Qt.DisplayRole:
            return item.name
        if role == Qt.DecorationRole:
            return item.icon
        if role == Qt.CheckStateRole:
            return item.checked
        return None

    def setData(self, index, value, role=Qt.EditRole):
        item = self._index_item(index)
        if item is None:
            return False
        if role == Qt.CheckStateRole:
            item.checked = value
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True
        return False

    def _index_item(self, index):
        if not index.isValid():
            return None
        row = index.row()
        if row < 0 or row >= len(self._items):
            return None
        return self._items[row]

    def load_data(self, entries):
        self.modelAboutToBeReset.emit()
        self._items = entries
        self.modelReset.emit()

    def flags(self, index):
        if index.isValid():
            return Qt.ItemIsUserCheckable | Qt.ItemIsEnabled
        return 0

    def checked_channels(self):
        return [i.name for i in self._items if i.checked]
