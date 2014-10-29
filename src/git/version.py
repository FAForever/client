__author__ = 'Sheeo'

import os
import re
import pygit2
from urlparse import urlparse

import json

import logging
logger = logging.getLogger(__name__)

from collections import namedtuple

TRUSTED_REPOS = ['github.com/FAForever/fa.git']
DEFAULT_REPO_URL_BASE = 'http://github.com/'

RepositoryVersion = namedtuple("RepositoryVersion", "repo ref url hash")


class Version():
    """
    Describes the version of a Repository.

    We track "stableness" and "trustedness" of a repository with the following rules:
     - A version is "stable" iff it has a commithash
     - A version is "trusted" iff the repository is in TRUSTED_REPOS (Implementation subject to change)
    """
    def __init__(self, *args, **kwargs):
        self._version = {}
        if len(args) == 2:
            self._version['repo'] = args[0]
            self._version['ref'] = args[1]
        elif len(args) == 4:
            self._version['repo'] = args[0]
            self._version['ref'] = args[1]
            self._version['url'] = args[2]
            self._version['hash'] = args[3]
        elif len(args) == 1:
            for k, v in json.loads(args[0]).iteritems():
                self[k] = v

    def __setitem__(self, key, value):
        self._version[key] = value

    @property
    def url(self):
        if 'url' in self._version:
            return self._version['url']
        else:
            return "".join([DEFAULT_REPO_URL_BASE, self._version['repo'], ".git"])

    @property
    def ref(self):
        if 'ref' in self._version:
            return self._version['ref']

    @property
    def repo(self):
        if 'repo' in self._version:
            return self._version['repo']

    @property
    def hash(self):
        if 'hash' in self._version:
            return self._version['hash']

    @property
    def is_stable(self):
        return self.hash is not None

    @property
    def is_trusted(self):
        parsed_url = urlparse(self.url)
        return len(filter(lambda url: parsed_url.netloc + parsed_url.path == url, TRUSTED_REPOS)) > 0
