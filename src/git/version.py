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
    def __init__(self, *args):
        if len(args) > 1:
            self._version = dict(zip(['repo', 'ref', 'url', 'hash'], args))
        elif len(args) == 1:
            self._version = dict()
            json_object = json.loads(args[0])
            for k in ['repo', 'ref', 'url', 'hash']:
                try:
                    self._version[k] = json_object[k]
                except KeyError:
                    pass
        for k in ['repo', 'ref']:
            if not k in self._version:
                raise KeyError

    def __eq__(self, other):
        if not self.hash is None:
            return self.hash == other.hash
        elif (self.repo, self.ref) is not (None, None):
            return self.repo == other.repo and self.ref == other.ref
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def url(self):
        if 'url' in self._version:
            return self._version['url']
        else:
            return "".join([DEFAULT_REPO_URL_BASE, self._version['repo'], ".git"])

    @property
    def ref(self):
        return self._version['ref']

    @property
    def repo(self):
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

    def to_json(self):
        return json.dumps(self._version)
