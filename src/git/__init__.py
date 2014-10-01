import os
from PyQt4 import QtCore
import pygit2

import logging
logger = logging.getLogger(__name__)


__author__ = 'Thygrrr'

class RepositoryBusyException(Exception):
    pass

class Repository(QtCore.QThread):
    operation_complete = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.repo = None
        self.remote = None
        self.url = None
        self.path = None
        self.refname = None
        self.run = None


    def __open(self):
        if not os.path.exists(self.path):
            logger.info("Cloning " + self.url + " into " + self.path)
            self.repo = pygit2.clone_repository(self.url, self.path)
            self.remote = self.repo.remotes[0]
        else:
            logger.info("Opening repository at " + self.path)
            self.repo = pygit2.Repository(self.path)

            logger.info("Fetching repository " + self.path)
            self.remote = self.repo.remotes[0]
            self.remote.fetch()

        logger.info("Checking out " + self.refname + " in " + self.path)
        self.repo.checkout(self.repo.lookup_branch(self.refname, pygit2.GIT_BRANCH_REMOTE), strategy=pygit2.GIT_CHECKOUT_FORCE)

        self.operation_complete.emit()

    def checkout(self, url, path, refname="origin/master"):
        self.url = url
        self.path = path
        self.refname = refname

        self.run = self.__open
        self.start()

