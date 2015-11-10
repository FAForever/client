import random

from util import logger

import json

import util


class Players:
    """
    Wrapper for an id->Player map

    Used to lookup players either by id (cheap) or by login (expensive, don't do this).
    
    Also responsible for general player logic, e.g remembering friendliness and colors of players.
    """
    def __init__(self):
        self._players = {}
        self._warned = False
        self.login = None
        self.coloredNicknames = False
        
        # names of the client's friends
        self.friends = set()
        
        # names of the client's foes
        self.foes = set()
        
        # names of the client's clanmates
        self.clanlist = set()



    #Color table used by the following method
    # CAVEAT: This will break if the theme is loaded after the client package is imported
    colors = json.loads(util.readfile("client/colors.json"))
    randomcolors = json.loads(util.readfile("client/randomcolors.json"))

    def isFriend(self, name):
        '''
        Convenience function for other modules to inquire about a user's friendliness.
        '''
        return name in self.friends

    def isFoe(self, name):
        '''
        Convenience function for other modules to inquire about a user's foeliness.
        '''
        return name in self.foes

    def isPlayer(self, name):
        '''
        Convenience function for other modules to inquire about a user's civilian status.
        '''
        return name in self or name == self.login

    def getUserColor(self, name):
        '''
        Returns a user's color depending on their status with relation to the FAF client
        '''
        if name == self.login:
            return self.getColor("self")
        elif name in self.friends:
            return self.getColor("friend")
        elif name in self.foes:
            return self.getColor("foe")
        elif name in self.clanlist:
            return self.getColor("clan")
        else:
            if self.coloredNicknames:
                return self.getRandomColor(name)

            if name in self:
                return self.getColor("player")

            return self.getColor("default")

    def getRandomColor(self, name):
        '''Generate a random color from a name'''
        random.seed(name)
        return random.choice(self.randomcolors)

    def getColor(self, name):
        if name in self.colors:
            return self.colors[name]
        else:
            return self.colors["default"]


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
