__author__ = 'Thygrrr'

import os
import pygit2

import logging
logger = logging.getLogger(__name__)

print(pygit2.LIBGIT2_VERSION)

class Repository():
    def __init__(self, path, url):
        self.path = path
        self.url = url

        logger.info("Opening repository at " + self.path)
        if not os.path.exists(self.path):
            self.repo = pygit2.init_repository(self.path)
        else:
            self.repo = pygit2.Repository(self.path)

        if not self.url in [remote.url for remote in self.repo.remotes]:
            logger.info("Adding remote " + self.path)
            self.repo.create_remote("origin", self.url)




    @property
    def tags(self):
        regex = re.compile('^refs/tags')
        return filter(lambda r: regex.match(r), repo.listall_references())


    @property
    def branches(self):
        regex = re.compile('^refs/heads')
        return filter(lambda r: regex.match(r), repo.listall_references())


    def fetch(self):
        for remote in self.repo.remotes:
            logger.info("Fetching '" + remote.name + "' from " + remote.url)
            remote.fetch()

    def checkout(self, refname="origin/master"):
        logger.info("Checking out " + refname + " in " + self.path)
        self.repo.set_head("refs/remotes/origin/master")
        self.repo.checkout(self.repo.lookup_branch(refname, pygit2.GIT_BRANCH_REMOTE), strategy=pygit2.GIT_CHECKOUT_FORCE)

