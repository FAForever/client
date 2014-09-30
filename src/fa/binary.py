from PyQt4.QtGui import QProgressDialog

__author__ = 'Thygrrr'

import pygit2

from PyQt4 import QtGui, QtCore
import os
import util

import logging
logger = logging.getLogger(__name__)

REPO_NAME = "binary-patch"


class RepoOperation(QtCore.QThread):
    def __init__(self, name, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.repo = None
        self.remote = None
        self.REPOSITORY_URL = "https://github.com/FAForever/" + name + ".git"
        self.REPOSITORY_DIR = os.path.join(util.REPO_DIR, name)

    def open(self):
        if not os.path.exists(self.REPOSITORY_DIR):
            self.repo = pygit2.clone_repository(self.REPOSITORY_URL, self.REPOSITORY_DIR)
        else:
            self.repo = pygit2.Repository(self.REPOSITORY_DIR)

        def transfer_progress(stats):
            logger.info(stats.received_bytes)

        self.remote = self.repo.remotes[0]
        self.remote.transfer_progress = transfer_progress

    def run(self):
            self.remote.fetch()
            self.repo.checkout(self.repo.lookup_branch("origin/master", pygit2.GIT_BRANCH_REMOTE), strategy=pygit2.GIT_CHECKOUT_FORCE)



class Updater(QtCore.QObject):
    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)
        self.thread = RepoOperation(REPO_NAME, self)
        self.progress = QProgressDialog("Checking out " + REPO_NAME, "Cancel", 0, 0)
        self.progress.setWindowTitle("Updater")
        self.progress.show()
        self.thread.open()
        self.thread.finished.connect(self.progress.hide)
        self.thread.start()

