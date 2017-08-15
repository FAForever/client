import util
import json
import random
from enum import Enum


def _loadcolors(filename):
    return json.loads(util.THEME.readfile(filename))


class PlayerAffiliation(Enum):
    SELF = "self"
    FRIEND = "friend"
    FOE = "foe"
    CLANNIE = "clan"
    OTHER = "default"


class PlayerColors:
    # Color table used by the following method
    # CAVEAT: will break if theme is loaded after client module is imported
    colors = _loadcolors("client/colors.json")
    operatorColors = _loadcolors("chat/formatters/operator_colors.json")
    randomcolors = _loadcolors("client/randomcolors.json")

    def __init__(self, user):
        self._user = user
        self.coloredNicknames = False

    def getColor(self, name):
        if name in self.colors:
            return self.colors[name]
        else:
            return self.colors["default"]

    def getRandomColor(self, seed):
        '''Generate a random color from a seed'''
        random.seed(seed)
        return random.choice(self.randomcolors)

    def getAffiliation(self, id_=-1, name=None):
        if self._user.player and self._user.player.id == id_:
            return PlayerAffiliation.SELF
        if self._user.isFriend(id_, name):
            return PlayerAffiliation.FRIEND
        if self._user.isFoe(id_, name):
            return PlayerAffiliation.FOE
        if self._user.isClannie(id_):
            return PlayerAffiliation.CLANNIE
        return PlayerAffiliation.OTHER

    def getUserColor(self, _id=-1, name=None):
        affil = self.getAffiliation(_id, name)
        names = {
            PlayerAffiliation.SELF: "self",
            PlayerAffiliation.FRIEND: "friend",
            PlayerAffiliation.FOE: "foe",
            PlayerAffiliation.CLANNIE: "clan",
        }

        if affil in names:
            return self.getColor(names[affil])
        if self.coloredNicknames:
            return self.getRandomColor(_id if _id != -1 else name)

        if _id == -1:   # IRC user
            return self.getColor("default")
        return self.getColor("player")

    def getModColor(self, elevation, _id=-1, name=None):
        affil = self.getAffiliation(_id, name)
        names = {
            PlayerAffiliation.SELF: "self_mod",
            PlayerAffiliation.FRIEND: "friend_mod",
            PlayerAffiliation.CLANNIE: "friend_mod",
        }

        if affil in names:
            return self.getColor(names[affil])

        if elevation in self.operatorColors:
                return self.operatorColors[elevation]

        return self.getColor("player")
