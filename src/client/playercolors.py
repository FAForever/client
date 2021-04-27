import json
import random
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal


class PlayerAffiliation(Enum):
    SELF = "self"
    FRIEND = "friend"
    FOE = "foe"
    CLANNIE = "clan"
    CHATTERBOX = "chatterbox"
    OTHER = "default"


class PlayerColors(QObject):
    changed = pyqtSignal()

    def __init__(self, me, user_relations, theme):
        QObject.__init__(self)
        self._me = me
        self._user_relations = user_relations
        self._theme = theme
        self._colored_nicknames = False
        self.colors = self._load_colors("client/colors.json")
        self.random_colors = self._load_colors("client/randomcolors.json")

    @property
    def colored_nicknames(self):
        return self._colored_nicknames

    @colored_nicknames.setter
    def colored_nicknames(self, value):
        self._colored_nicknames = value
        self.changed.emit()

    def _load_colors(self, filename):
        return json.loads(self._theme.readfile(filename))

    def get_color(self, name):
        if name in self.colors:
            return self.colors[name]
        else:
            return self.colors["default"]

    def _seed(self, id_, name):
        return id_ if id_ not in [-1, None] else name

    def get_random_color(self, id_, name):
        random.seed(self._seed(id_, name))
        return random.choice(self.random_colors)

    def get_random_color_index(self, id_, name):
        random.seed(self._seed(id_, name))
        return random.choice(range(len(self.random_colors)))

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
        if self._user_relations.is_chatterbox(_id, name):
            return self.get_chatterbox_color(_id, name)

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
            return self.get_random_color(_id, name)

        if _id == -1:   # IRC user
            return self.get_color("default")
        return self.get_color("player")

    def get_mod_color(self, _id=-1, name=None):
        affil = self._get_affiliation(_id, name)
        names = {
            PlayerAffiliation.SELF: "self_mod",
            PlayerAffiliation.FRIEND: "friend_mod",
            PlayerAffiliation.CLANNIE: "friend_mod",
        }
        if affil in names:
            return self.get_color(names[affil])
        return self.get_color("mod")

    def get_chatterbox_color(self, _id=-1, name=None):
        affil = self._get_affiliation(_id, name)
        names = {
            PlayerAffiliation.FRIEND: "friend_chatterbox",
            PlayerAffiliation.FOE: "foe_chatterbox",
            PlayerAffiliation.CLANNIE: "clan_chatterbox",
        }
        if affil in names:
            return self.get_color(names[affil])
        return self.get_color("chatterbox")
