import json
import random
from enum import Enum


class PlayerAffiliation(Enum):
    SELF = "self"
    FRIEND = "friend"
    FOE = "foe"
    CLANNIE = "clan"
    OTHER = "default"


class PlayerColors:
    def __init__(self, me, user_relations, theme):
        self._me = me
        self._user_relations = user_relations
        self._theme = theme
        self.colored_nicknames = False
        self._colors = self._load_colors("client/colors.json")
        self._operator_colors = self._load_colors(
                "chat/formatters/operator_colors.json")
        self._random_colors = self._load_colors("client/randomcolors.json")

    def _load_colors(self, filename):
        return json.loads(self._theme.readfile(filename))

    def get_color(self, name):
        if name in self._colors:
            return self._colors[name]
        else:
            return self._colors["default"]

    def get_random_color(self, seed):
        '''Generate a random color from a seed'''
        random.seed(seed)
        return random.choice(self._random_colors)

    def _get_affiliation(self, id_=-1, name=None):
        if self._me.player is not None and self._me.player.id == id_:
            return PlayerAffiliation.SELF
        if self._user_relations.is_friend(id_, name):
            return PlayerAffiliation.FRIEND
        if self._user_relations.is_foe(id_, name):
            return PlayerAffiliation.FOE
        if self._me.is_clannie(id_):
            return PlayerAffiliation.CLANNIE
        return PlayerAffiliation.OTHER

    def get_user_color(self, _id=-1, name=None):
        affil = self._get_affiliation(_id, name)
        names = {
            PlayerAffiliation.SELF: "self",
            PlayerAffiliation.FRIEND: "friend",
            PlayerAffiliation.FOE: "foe",
            PlayerAffiliation.CLANNIE: "clan",
        }

        if affil in names:
            return self.get_color(names[affil])
        if self.colored_nicknames:
            return self.get_random_color(_id if _id != -1 else name)

        if _id == -1:   # IRC user
            return self.get_color("default")
        return self.get_color("player")

    def get_mod_color(self, elevation, _id=-1, name=None):
        affil = self._get_affiliation(_id, name)
        names = {
            PlayerAffiliation.SELF: "self_mod",
            PlayerAffiliation.FRIEND: "friend_mod",
            PlayerAffiliation.CLANNIE: "friend_mod",
        }

        if affil in names:
            return self.get_color(names[affil])

        if elevation in self._operator_colors:
                return self._operator_colors[elevation]

        return self.get_color("player")
