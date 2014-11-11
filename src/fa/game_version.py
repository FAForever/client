__author__ = 'Sheeo'

from git import Repository, Version
from fa import featured

from collections import namedtuple


class GameVersion():
    """
    For describing the exact version of FA used.
    """

    def __init__(self, dict):
        self._versions = dict

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
               and self._versions['game'].version.is_stable \
               and all(map(lambda x: x.version.is_stable, self._versions['mods']))

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
            return isinstance(mod, featured.FeaturedMod) \
                   and valid_version(mod.version) and featured.is_featured_mod(mod)

        def valid_mod(mod):
            return True

        valid = "engine" in self._versions
        valid = valid and "game" in self._versions
        for key, value in self._versions.iteritems():
            valid = valid and {
                'engine': lambda version: valid_version(version),
                'game': lambda mod: valid_featured_mod(mod),
                'mods': lambda versions: any(versions)
                                         and all(map(lambda v: valid_mod(v), versions)),
            }.get(key, lambda k: True)(value)

        return valid

    @property
    def is_trusted(self):
        """
        Trustedness means that all repos referenced are trusted
        :return bool
        """
        trusted = self._versions['engine'].is_trusted
        trusted = trusted and self._versions['game'].is_trusted
        return trusted and reduce(lambda x, y: x.is_trusted and y.is_trusted, self._versions['mods'])

    @property
    def untrusted_urls(self):
        urls = []
        if not self._versions['engine'].is_trusted:
            urls.append(self._versions['engine'].url)
        if not self._versions['game'].version.is_trusted:
            urls.append(self._versions['game'].version.url)
        return urls
