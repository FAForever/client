from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTextEdit

from src.replays.replaydetails.replayreader import ReplayParser


class ChatTab(QTextEdit):
    def __init__(self) -> None:
        super().__init__()
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setReadOnly(True)

    def initialize(self, replay: ReplayParser) -> None:
        self.setHtml(replay.get_chat())
