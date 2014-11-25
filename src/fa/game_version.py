__author__ = 'Sheeo'

from config import Settings

from git import Repository, Version
from fa.mod import Mod

import json


class GameVersionError(Exception):
    def __init__(self, msg):
        super(GameVersionError, self).__init__(self, msg)


class GameVersion():
    """
    For describing the exact version of FA used.
    """

    def __init__(self, engine, main_mod, mods=None, _map=None):
        if not isinstance(main_mod, Mod):
            raise GameVersionError("Not a loadable mod: " + repr(main_mod))
        if not all(map(lambda m: isinstance(m, Mod), mods)):
            raise GameVersionError("Not all mods given are loadable mods")
        self._versions = dict({'engine': engine,
                               'main_mod': main_mod,
                               'mods': mods,
                               'map': _map})
        if not self._is_valid:
            raise GameVersionError("Invalid game version: " + repr(self._versions))

    @staticmethod
    def from_dict(dictionary):
        try:
            return GameVersion(dictionary['engine'],
                               dictionary['main_mod'],
                               dictionary.get('mods'),
                               dictionary.get('map'))
        except (KeyError, ValueError):
            raise GameVersionError("Invalid GameVersion: %r" % dictionary)

    @property
    def _is_valid(self):
        """
        Validity means that the dictionary contains the
        required keys with instances of Version.

        :return: bool
        """

        def valid_version(version):
            return isinstance(version, Version)

        def valid_mod(mod):
            return isinstance(mod, Mod) \
                   and valid_version(mod.version)

        def valid_main_mod(mod):
            return valid_mod(mod) and mod.is_featured

        valid = "engine" in self._versions
        valid = valid and "main_mod" in self._versions
        for key, value in self._versions.iteritems():
            valid = valid and {
                'engine': lambda version: valid_version(version),
                'main_mod': lambda mod: valid_main_mod(mod),
                'mods': lambda versions: all(map(lambda v: valid_mod(v), versions)),
                }.get(key, lambda k: True)(value)

        return valid

    @property
    def is_stable(self):
        """
        Stable means that this version of the game is a fixed pointer, i.e.:

            No refs point to a branch and we have commit hashes
            for every repo version.
        :return: bool
        """
        return self._versions['engine'].is_stable \
            and self._versions['main_mod'].version.is_stable \
            and all(map(lambda x: x.version.is_stable, self._versions['mods']))

    @property
    def repos(self):
        repos = [Repository(Settings.get('ENGINE_PATH', 'FA')),
                 Repository(self.main_mod.path)]
        for m in self.mods:
            repos.append(Repository(m.path))
        return repos

    @property
    def repo_versions(self):
        repos = self.repos
        versions = [self.engine, self.main_mod.version, map(lambda m: m.version, self.mods)]
        return zip(repos, versions)

    @property
    def engine_repo(self):
        return Repository(Settings.get('ENGINE_PATH', 'FA'))

    @property
    def main_mod_repo(self):
        return Repository(self.main_mod.path)

    @property
    def engine(self):
        return self._versions['engine']

    @property
    def main_mod(self):
        return self._versions['main_mod']

    @property
    def mods(self):
        return self._versions['mods']

    @property
    def map(self):
        return self._versions['map']

    @property
    def is_trusted(self):
        """
        Trustedness means that all repos referenced are trusted
        :return bool
        """
        trusted = self.engine.is_trusted
        trusted = trusted and self.main_mod.version.is_trusted
        if len(self.mods) > 0:
            return trusted and reduce(lambda x, y: x.is_trusted and y.is_trusted, self._versions['mods'])
        else:
            return trusted

    @property
    def untrusted_urls(self):
        urls = []
        if not self.engine.is_trusted:
            urls.append(self.engine.url)
        if not self.main_mod.version.is_trusted:
            urls.append(self.main_mod.version.url)
        return urls

    @staticmethod
    def serialize_kids(obj):
        if isinstance(obj, Mod):
            return Mod.to_dict(obj)
        elif isinstance(obj, Version):
            return Version.to_dict(obj)
        else:
            raise TypeError(repr(obj) + " is not JSON serializable")

    def to_json(self):
        return json.dumps(self._versions, default=self.serialize_kids)

    @staticmethod
    def from_default_version(result):
        return GameVersion.from_dict(result)
