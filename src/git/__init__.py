import os
import pygit2

import logging
logger = logging.getLogger(__name__)


__author__ = 'Thygrrr'


class Repository():
    def __init__(self, url, path):
        self.repo = None
        self.remote = None

        self.url = url
        self.path = path


    def __checkout(self, refname):
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

        logger.info("Checking out " + refname + " in " + self.path)
        self.repo.checkout(self.repo.lookup_branch(refname, pygit2.GIT_BRANCH_REMOTE), strategy=pygit2.GIT_CHECKOUT_FORCE)


    def checkout(self, refname="origin/master"):
        self.__checkout(refname)

