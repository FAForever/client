__author__ = 'Sheeo'

import os
import re
import pygit2

from urlparse import urlparse
import fnmatch
import posixpath

import json

import logging
logger = logging.getLogger(__name__)

from collections import namedtuple

TRUSTED_REPOS = ['github.com/FAForever/*',
                 'git.faforever.com/*']
DEFAULT_REPO_URL_BASE = 'http://github.com/'

RepositoryVersion = namedtuple("RepositoryVersion", "repo ref url hash")


class Version():
    """
    Describes the version of a Repository.

    We track "stableness" and "trustedness" of a repository with the following rules:
     - A version is "stable" iff it has a commithash
     - A version is "trusted" iff the repository is in TRUSTED_REPOS (Implementation subject to change)
    """
    def __init__(self, repo, ref, url=None, hash=None):
        self._version = {"repo": repo, "ref": ref, "url": url, "hash": hash}

    @staticmethod
    def from_json(string):
        json_object = json.loads(string)
        return Version.from_dict(json_object)

    @staticmethod
    def from_dict(dictionary):
        return Version(dictionary['repo'],
                       dictionary['ref'],
                       dictionary.get('url'),
                       dictionary.get('hash'))

    def __eq__(self, other):
        if not isinstance(other, Version):
            return False
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
        if self._version['url'] is not None:
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
    def repo_name(self):
        return posixpath.basename(self.repo)

    @property
    def repo_author(self):
        return posixpath.dirname(self.repo)

    @property
    def is_stable(self):
        return self.hash is not None

    @property
    def is_trusted(self):
        parsed_url = urlparse(self.url)
        return len(filter(lambda url: fnmatch.fnmatch(parsed_url.hostname + parsed_url.path, url), TRUSTED_REPOS)) > 0

    def __repr__(self):
        return "(repo: %s,ref: %s, url: %s, hash: %s)" % (self.repo, self.ref, self.url, self.hash)

    def to_json(self):
        return json.dumps(self._version)

    def to_dict(self):
        return self._version
