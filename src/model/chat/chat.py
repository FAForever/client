from PyQt5.QtCore import QObject


class Chat(QObject):
    def __init__(self, chatterset, channelset):
        QObject.__init__(self)
        self.chatters = chatterset
        self.channels = channelset
