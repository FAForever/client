from util import logger


class Players:
    """
    Wrapper for an id->Player map

    Used to lookup players either by id (cheap) or by login (expensive, don't do this).

    In the future could contain more responsibility, e.g. emitting signals when players are updated.
    """
    def __init__(self):
        self._players = {}
        self._warned = False
        
        # names of the client's friends
        self.friends = set()
        
        # names of the client's foes
        self.foes = set()
        
        # names of the client's clanmates
        self.clanlist = set()

    def keys(self):
        return self._players.keys()

    def values(self):
        return self._players.values()

    def items(self):
        return self._players.items()

    def get(self, item, default):
        val = self.__getitem__(item)
        return val if val else default

    def __contains__(self, item):
        return self.__getitem__(item) is not None

    def __getitem__(self, item):
        if item in self._players:
            return self._players[item]
        else:
            if not self._warned:
                logger.warning("Expensive lookup by player login, FIXME.")
                self._warned = True
            by_login = {p.login: p for _, p in self._players.items()}
            if item in by_login:
                return by_login[item]

    def __setitem__(self, key, value):
        self._players[key] = value
