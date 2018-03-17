class ChatLineRestorer:
    def __init__(self, model):
        self._model = model
        self._saved_channels = {}
        self._model.channels.added.connect(self._at_channel_added)
        self._model.channels.removed.connect(self._at_channel_removed)

    def _at_channel_removed(self, channel):
        self._save_channel_lines(channel)

    def _save_channel_lines(self, channel):
        self._saved_channels[channel.id_key] = [line for line in channel.lines]

    def _at_channel_added(self, channel):
        self._restore_channel_lines(channel)

    def _restore_channel_lines(self, channel):
        saved = self._saved_channels.get(channel.id_key, None)
        if saved is None:
            return
        for line in saved:
            channel.lines.add_line(line)
        del self._saved_channels[channel.id_key]
