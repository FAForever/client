
"""
Created on Dec 8, 2011

@author: thygrrr
"""
from PyQt5 import QtCore, QtWidgets


class ChatLineEdit(QtWidgets.QLineEdit):
    """
    A special promoted QLineEdit that is used in channel.ui to provide a
    mirc-style editing experience with completion and history.
    LATER: History and tab completion support
    """

    def __init__(self, parent):
        QtWidgets.QLineEdit.__init__(self, parent)
        self.returnPressed.connect(self.on_line_entered)
        self.history = []
        self.currentHistoryIndex = None
        self.historyShown = False
        self.completionStarted = False
        self.channel = None
        self.LocalChatterNameList = []
        self.currenLocalChatter = None

    def set_channel(self, channel):
        self.channel = channel

    def event(self, event):
        if event.type() == QtCore.QEvent.KeyPress:
            # Swallow a selection of keypresses that we want for our history
            # support.
            if event.key() == QtCore.Qt.Key_Tab:
                self.try_completion()
                return True
            elif event.key() == QtCore.Qt.Key_Space:
                self.accept_completion()
                return QtWidgets.QLineEdit.event(self, event)
            elif event.key() == QtCore.Qt.Key_Up:
                self.cancel_completion()
                self.prev_history()
                return True
            elif event.key() == QtCore.Qt.Key_Down:
                self.cancel_completion()
                self.next_history()
                return True
            else:
                self.cancel_completion()
                return QtWidgets.QLineEdit.event(self, event)

        # All other events (non-keypress)
        return QtWidgets.QLineEdit.event(self, event)

    @QtCore.pyqtSlot()
    def on_line_entered(self):
        self.history.append(self.text())
        self.currentHistoryIndex = len(self.history) - 1

    def showEvent(self, event):
        self.setFocus(True)
        return QtWidgets.QLineEdit.showEvent(self, event)

    def try_completion(self):
        if not self.completionStarted:
            # no completion on empty line
            if self.text() == "":
                return
            # no completion if last character is a space
            if self.text().rfind(" ") == (len(self.text()) - 1):
                return

            self.completionStarted = True
            self.LocalChatterNameList = []
            # take last word from line
            self.completionText = self.text().split()[-1]
            # store line to be completed without the completion string
            self.completionLine = self.text().rstrip(self.completionText)

            # make a copy of users because the list might change frequently
            # giving all kind of problems
            if self.channel is not None:
                for cc in self.channel.chatters.values():
                    name = cc.chatter.name
                    if name.lower().startswith(self.completionText.lower()):
                        self.LocalChatterNameList.append(name)

            if len(self.LocalChatterNameList) > 0:
                self.LocalChatterNameList.sort(
                    key=lambda chatter: chatter.lower(),
                )
                self.currenLocalChatter = 0
                localName = self.LocalChatterNameList[self.currenLocalChatter]
                self.setText(self.completionLine + localName)
            else:
                self.currenLocalChatter = None
        else:
            if self.currenLocalChatter is not None:
                self.currenLocalChatter += 1
                self.currenLocalChatter %= len(self.LocalChatterNameList)
                localName = self.LocalChatterNameList[self.currenLocalChatter]
                self.setText(self.completionLine + localName)

    def accept_completion(self):
        self.completionStarted = False

    def cancel_completion(self):
        self.completionStarted = False

    def prev_history(self):
        if self.currentHistoryIndex is not None:  # no history nothing to do
            # check for boundaries and only change index is history is already
            # shown
            if self.currentHistoryIndex > 0 and self.historyShown:
                self.currentHistoryIndex -= 1
            self.historyShown = True
            self.setText(self.history[self.currentHistoryIndex])

    def next_history(self):
        if self.currentHistoryIndex is not None:
            # check for boundaries and only change index is history is already
            # shown
            if (
                self.currentHistoryIndex < len(self.history) - 1
                and self.historyShown
            ):
                self.currentHistoryIndex += 1
            self.historyShown = True
            self.setText(self.history[self.currentHistoryIndex])
