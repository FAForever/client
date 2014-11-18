__author__ = 'Sheeo'

from git import Repository, Version
from fa import featured

from collections import namedtuple


class GameVersion():
    """
    For describing the exact version of FA used.
    """
    def __init__(self, engine, main_mod, mods=None, _map=None):
        self._versions = dict({'engine': engine,
                               'main_mod': main_mod,
                               'mods': mods,
                               'map': _map})

    @staticmethod
    def from_dict(dictionary):
        return GameVersion(dictionary['engine'],
                           dictionary['main_mod'],
                           dictionary.get('mods'),
                           dictionary.get('map'))

    @property
    def is_stable(self):
        """
        Stable means that this version of the game is a fixed pointer, i.e.:

            No refs point to a branch and we have commit hashes
            for every repo version.
        :return: bool
        """
        return self.is_valid \
               and self._versions['engine'].is_stable \
               and self._versions['main_mod'].version.is_stable \
               and all(map(lambda x: x.version.is_stable, self._versions['mods']))

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
    def is_valid(self):
        """
        Validity means that the dictionary contains the
        required keys with instances of Version.

        :return: bool
        """

        def valid_version(version):
            return isinstance(version, Version)

        def valid_featured_mod(mod):
            return isinstance(mod, featured.Mod) \
                   and valid_version(mod.version) and featured.is_featured_mod(mod)

        def valid_mod(mod):
            return True

        valid = "engine" in self._versions
        valid = valid and "main_mod" in self._versions
        for key, value in self._versions.iteritems():
            valid = valid and {
                'engine': lambda version: valid_version(version),
                'main_mod': lambda mod: valid_featured_mod(mod),
                'mods': lambda versions: all(map(lambda v: valid_mod(v), versions)),
            }.get(key, lambda k: True)(value)

        return valid

    @property
    def is_trusted(self):
        """
        Trustedness means that all repos referenced are trusted
        :return bool
        """
        trusted = self.engine.is_trusted
        trusted = trusted and self.main_mod.is_trusted
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
