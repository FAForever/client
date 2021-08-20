from enum import Enum

from PyQt5.QtCore import QUrl, QUrlQuery


class GameUrlType(Enum):
    LIVE_REPLAY = "faflive"
    OPEN_GAME = "fafgame"


class GameUrl:
    LOBBY_URL = "lobby.faforever.com"
    REPLAY_SUFFIX = ".SCFAreplay"

    def __init__(self, game_type, map_, mod, uid, player, mods=None):
        self.game_type = game_type
        self.map = map_
        self.mod = mod
        self.mods = mods
        self.uid = uid
        self.player = player    # Can be both name and uid

    def to_url(self):
        url = QUrl()
        url.setHost(self.LOBBY_URL)
        url.setScheme(self.game_type.value)
        query = QUrlQuery()
        query.addQueryItem("map", self.map)
        query.addQueryItem("mod", self.mod)
        if self.mods is not None:
            query.addQueryItem("mods", self.mods)

        if self.game_type == GameUrlType.OPEN_GAME:
            url.setPath("/{}".format(self.player))
            query.addQueryItem("uid", str(self.uid))
        else:
            url.setPath(
                "/{}/{}{}".format(self.uid, self.player, self.REPLAY_SUFFIX),
            )

        url.setQuery(query)
        return url

    @classmethod
    def from_url(cls, url):
        try:
            url = QUrl(url)
            query = QUrlQuery(url)
            map_ = cls._get_query_item(query, "map")
            mod = cls._get_query_item(query, "mod")
            game_type = GameUrlType(url.scheme())

            path = url.path().split("/")

            if game_type == GameUrlType.OPEN_GAME:
                uid = cls._get_query_item(query, "uid", int)
                player = path[1]
            else:
                uid = int(path[1])
                player = path[2]
                if not player.endswith(cls.REPLAY_SUFFIX):
                    raise ValueError
                player = player[:-len(cls.REPLAY_SUFFIX)]

        except (ValueError, TypeError, IndexError):
            raise ValueError

        try:
            mods = cls._get_query_item(query, "mods")
        except ValueError:
            mods = None
        return cls(game_type, map_, mod, uid, player, mods)

    @classmethod
    def _get_query_item(cls, query, name, type_=str):
        str_value = query.queryItemValue(name)
        if str_value == "":
            raise ValueError
        return type_(str_value)

    @classmethod
    def is_game_url(cls, url):
        return QUrl(url).scheme() in [e.value for e in GameUrlType]
