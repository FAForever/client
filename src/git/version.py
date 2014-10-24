__author__ = 'Sheeo'

import os
import re
import pygit2
from urlparse import urlparse

import logging
logger = logging.getLogger(__name__)

from collections import namedtuple

TRUSTED_REPOS = ['github.com/FAForever/fa.git']
DEFAULT_REPO_URL_BASE = 'http://github.com/'

RepositoryVersion = namedtuple("RepositoryVersion", "repo ref url hash")

class Version():
    def __init__(self, repo, ref, url = None, hash=None):
        self._version = RepositoryVersion(repo,ref,url,hash)

    @property
    def url(self):
        if self._version.url:
            return self._version.url
        else:
            return "".join([DEFAULT_REPO_URL_BASE, self._version.repo, ".git"])

    @property
    def is_stable(self):
        return self._version.hash is not None

    @property
    def is_trusted(self):
        parsed_url = urlparse(self.url)
        return len(filter(lambda url: parsed_url.netloc + parsed_url.path == url, TRUSTED_REPOS)) > 0
