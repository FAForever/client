import util
import json
import random
from client.user import PlayerAffiliation


def _loadcolors(filename):
    return json.loads(util.THEME.readfile(filename))


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

    def getUserColor(self, _id=-1, name=None):
        affil = self._user.getAffiliation(_id, name)
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
        affil = self._user.getAffiliation(_id, name)
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
