__author__ = 'Thygrrr'

import os
import re
import pygit2

import logging
logger = logging.getLogger(__name__)

from PyQt4 import QtCore, QtGui

class Repository(QtCore.QObject):

    transfer_progress_value = QtCore.pyqtSignal(int)
    transfer_progress_maximum = QtCore.pyqtSignal(int)
    transfer_complete = QtCore.pyqtSignal()

    def __init__(self, path, url, parent=None):
        QtCore.QObject.__init__(self, parent)

        assert url
        assert path

        self.path = path
        self.url = url

        logger.info("Opening repository at " + self.path)
        if not os.path.exists(self.path):
            self.repo = pygit2.init_repository(self.path)
        else:
            if not os.path.exists(os.path.join(self.path, ".git")):
                raise pygit2.GitError(self.path + " doesn't seem to be a git repo. libgit2 might crash.")
            self.repo = pygit2.Repository(self.path)

        if not "faf" in self.remote_names:
            logger.info("Adding remote 'faf' " + self.path)
            self.repo.create_remote("faf", self.url)

    def __del__(self):
        self.close()

    def close(self):
        del self.repo


    @property
    def tags(self):
        regex = re.compile('^refs/tags/(.*)')
        return [regex.match(r).group(1) for r in self.repo.listall_references() if regex.match(r)]


    @property
    def remote_branches(self):
        return self.repo.listall_branches(pygit2.GIT_BRANCH_REMOTE)


    @property
    def local_branches(self):
        return self.repo.listall_branches(pygit2.GIT_BRANCH_LOCAL)


    @property
    def remote_names(self):
        return [remote.name for remote in self.repo.remotes]


    @property
    def remote_urls(self):
        return [remote.url for remote in self.repo.remotes]


    @property
    def current_head(self):
        return self.repo.head.target


    def _sideband(self, operation):
        logger.debug(operation)


    def _transfer(self, transfer_progress):
        self.transfer_progress_value.emit(transfer_progress.indexed_deltas)
        self.transfer_progress_maximum.emit(transfer_progress.total_deltas)
        QtGui.QApplication.processEvents()

    def has_hex(self, hex):
        return self.repo.__contains__(hex)

    def has_version(self, version):
        ref_object = self.repo.get(self.repo.lookup_reference("refs/tags/"+version.ref).target)
        if isinstance(ref_object, pygit2.Tag):
            if ref_object.target:
                print self.has_hex(version.hash)
                return self.has_hex(version.hash) and ref_object.target.hex == version.hash
        return False

    def fetch(self):
        for remote in self.repo.remotes:
            logger.info("Fetching '" + remote.name + "' from " + remote.url)
            remote.sideband_progress = self._sideband
            remote.transfer_progress = self._transfer
            remote.fetch()

        # It's not entirely clear why this needs to happen, but libgit2 expects the head to point somewhere after fetch
        if self.repo.listall_references():
            self.repo.set_head(self.repo.listall_references()[0])

        self.transfer_complete.emit()


    def checkout(self, target="faf/master"):
        logger.info("Checking out " + target + " in " + self.path)
        if target in self.remote_branches:
            self.repo.checkout(self.repo.lookup_branch(target, pygit2.GIT_BRANCH_REMOTE), strategy=pygit2.GIT_CHECKOUT_FORCE)
        elif target in self.local_branches:
            self.repo.checkout(self.repo.lookup_branch(target, pygit2.GIT_BRANCH_LOCAL), strategy=pygit2.GIT_CHECKOUT_FORCE)
        elif target in self.tags:
            self.repo.checkout(self.repo.lookup_reference("refs/tags/" + target), strategy=pygit2.GIT_CHECKOUT_FORCE)
        else:
            reference = self.repo[target]
            self.repo.reset(reference.id, pygit2.GIT_RESET_HARD)


