__author__ = 'Sheeo'

from PyQt4.QtCore import *

import pygit2


class Fetcher(QThread):
    done = pyqtSignal()
    error = pyqtSignal(object)
    progress = pyqtSignal(str, int, int)

    def __init__(self, repo_versions, parent=None):
        super(QThread, self).__init__(parent)
        self._repo_versions = repo_versions

    def run(self):
        for r, v in self._repo_versions:
            text = "Fetching %s from %s" % (v.ref, v.url)
            self.progress.emit(text, 0, 0)
            r.progress.connect(lambda indexed, total: self.progress.emit(text, indexed, total))
            try:
                r.fetch_version(v)
            except pygit2.GitError as e:
                self.error.emit(e)
        self.done.emit()
