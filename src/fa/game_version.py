__author__ = 'Sheeo'

from config import Settings

from git import Repository, Version
from fa.mod import Mod

import os
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
        self.validate()

    @staticmethod
    def from_dict(dictionary):
        try:
            engine = dictionary['engine'] if isinstance(dictionary['engine'], Version)\
                                          else Version.from_dict(dictionary['engine'])
            main_mod = dictionary['main_mod'] if isinstance(dictionary['main_mod'], Mod)\
                                              else Mod.from_dict(dictionary['main_mod'])
            return GameVersion(engine,
                               main_mod,
                               dictionary.get('mods'),
                               dictionary.get('map'))
        except (KeyError, ValueError) as e:
            raise GameVersionError("Invalid GameVersion: %r, error: %r" % (dictionary, e))

    def validate(self):
        def valid_version(version):
            if not isinstance(version, Version):
                raise GameVersionError("Not a valid git version: %s" % version)

        def valid_mod(mod):
            if not isinstance(mod, Mod):
                raise GameVersionError("Not a loadable mod: %s" % mod)
            valid_version(mod.version)

        def valid_main_mod(mod):
            valid_mod(mod)
            if not mod.is_featured:
                raise GameVersionError("Cannot load %s as main mod" % mod)

        if not "engine" in self._versions:
            raise GameVersionError("No engine version specified")
        if not "main_mod" in self._versions:
            raise GameVersionError("No main mod version specified")

        for key, value in self._versions.iteritems():
            {
                'engine': lambda version: valid_version(version),
                'main_mod': lambda mod: valid_main_mod(mod),
                'mods': lambda versions: all(map(lambda v: valid_mod(v), versions))
            }.get(key, lambda k: True)(value)
        return True

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
        repos = [self.engine_repo,
                 self.main_mod_repo]
        for m in self.mods:
            repos.append(Repository(os.path.join(Settings.get('MODS_PATH', 'FA'), m.identifier)))
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
        return Repository(os.path.join(Settings.get('MODS_PATH', 'FA'), self.main_mod.identifier))

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

    def to_dict(self):
        return self._versions

    @staticmethod
    def from_default_version(result):
        return GameVersion.from_dict(result)
