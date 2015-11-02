from util import logger


class Players:
    def __init__(self):
        self._players = {}
        self._warned = False

    def keys(self):
        return self._players.keys()

    def values(self):
        return self._players.values()

    def items(self):
        return self._players.items()

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
