import random

from client import Player
from util import logger

import json

import util


class Players:
    """
    Wrapper for an id->Player map

    Used to lookup players either by id (cheap) or by login (expensive, don't do this).
    
    Also responsible for general player logic, e.g remembering friendliness and colors of players.
    """
    def __init__(self, me):
        self.me = me
        "Logged in player. Can be None if we're not connected."
        self.coloredNicknames = False

        # UID -> Player map
        self._players = {}
        # Login -> Player map
        self._logins = {}

        # ids of the client's friends
        self.friends = set()

        # ids of the client's foes
        self.foes = set()

        # names of the client's clanmates
        self.clanlist = set()



    #Color table used by the following method
    # CAVEAT: This will break if the theme is loaded after the client package is imported
    colors = json.loads(util.readfile("client/colors.json"))
    randomcolors = json.loads(util.readfile("client/randomcolors.json"))

    def isFriend(self, id):
        '''
        Convenience function for other modules to inquire about a user's friendliness.
        '''
        return id in self.friends

    def isFoe(self, id):
        '''
        Convenience function for other modules to inquire about a user's foeliness.
        '''
        return id in self.foes

    def isPlayer(self, name):
        '''
        Convenience function for other modules to inquire about a user's civilian status.
        '''
        return name in self

    def getUserColor(self, id):
        '''
        Returns a user's color depending on their status with relation to the FAF client
        '''
        # Return default color if we're not logged in
        if self.me is None:
            return self.getColor("default")

        if id == self.me.id:
            return self.getColor("self")
        if id in self.friends:
            return self.getColor("friend")
        if id in self.foes:
            return self.getColor("foe")
        if id in self.clanlist:
            return self.getColor("clan")
        if self.coloredNicknames:
            return self.getRandomColor(id)
        if id in self:
            return self.getColor("player")

        return self.getColor("default")

    def getRandomColor(self, id):
        '''Generate a random color from a name'''
        random.seed(id)
        return random.choice(self.randomcolors)

    def getColor(self, name):
        if name in self.colors:
            return self.colors[name]
        else:
            return self.colors["default"]

    def keys(self):
        return list(self._players.keys())

    def values(self):
        return list(self._players.values())

    def items(self):
        return list(self._players.items())

    def get(self, item, default):
        val = self.__getitem__(item)
        return val if val else default

    def getID(self, name):
        if name in self._logins:
            return self._logins[name].id
        return -1

    def __contains__(self, item):
        return self.__getitem__(item) is not None

    def __getitem__(self, item):
        if isinstance(item, Player):
            return item
        if isinstance(item, int) and item in self._players:
            return self._players[item]
        if item in self._logins:
                return self._logins[item]

    def __setitem__(self, key, value):
        assert isinstance(key, int)
        self._players[key] = value
        self._logins[value.login] = value
