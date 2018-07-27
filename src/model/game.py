from PyQt5.QtCore import pyqtSignal, QUrl, QUrlQuery, QTimer

from enum import Enum
from decorators import with_logger
import time
import html

import string

from model.transaction import transactional
from model.modelitem import ModelItem
from util.gameurl import GameUrl, GameUrlType

class GameState(Enum):
    OPEN = "open"
    PLAYING = "playing"
    CLOSED = "closed"


# This enum has a counterpart on the server
class GameVisibility(Enum):
    PUBLIC = "public"
    FRIENDS = "friends"


@with_logger
class Game(ModelItem):
    """
    Represents a game happening on the server. Updates for the game state are
    sent from the server, identified by game uid. Updates are propagated with
    signals.

    The game with a given uid starts when we receive the first game message and
    ends with some update, or is ended manually. Once the game ends, it
    shouldn't be updated or ended again. Update and game end are propagated
    with signals.
    """
    before_replay_available = pyqtSignal(object, object)
    liveReplayAvailable = pyqtSignal(object)

    ingamePlayerAdded = pyqtSignal(object, object)
    ingamePlayerRemoved = pyqtSignal(object, object)

    OBSERVER_TEAMS = ['-1', 'null']
    LIVE_REPLAY_DELAY_SECS = 60 * 5

    def __init__(self,
                 playerset,
                 uid,
                 state,
                 launched_at,
                 num_players,
                 max_players,
                 title,
                 host,
                 mapname,
                 map_file_path,
                 teams,
                 featured_mod,
                 featured_mod_versions,
                 sim_mods,
                 password_protected,
                 visibility):

        ModelItem.__init__(self)

        self._playerset = playerset

        self.uid = uid
        self.add_field("state", state)
        self.add_field("launched_at", launched_at)
        self.add_field("num_players", num_players)
        self.add_field("max_players", max_players)
        self.add_field("title", title)
        self.add_field("host", host)
        self.add_field("mapname", mapname)
        self.add_field("map_file_path", map_file_path)
        self.add_field("teams", teams)
        self.add_field("featured_mod", featured_mod)
        self.add_field("featured_mod_versions", featured_mod_versions)
        self.add_field("sim_mods", sim_mods)
        self.add_field("password_protected", password_protected)
        self.add_field("visibility", visibility)
        self._aborted = False

        self._live_replay_timer = QTimer()
        self._live_replay_timer.setSingleShot(True)
        self._live_replay_timer.setInterval(self.LIVE_REPLAY_DELAY_SECS * 1000)
        self._live_replay_timer.timeout.connect(self._emit_live_replay)
        self.has_live_replay = False
        self._check_live_replay_timer()

    @property
    def id_key(self):
        return self.uid

    def copy(self):
        old = Game(self._playerset, self.uid, **self.field_dict)
        old._aborted = self._aborted
        old.has_live_replay = self.has_live_replay
        return old

    @transactional
    def update(self, **kwargs):
        if self._aborted:
            return

        _transaction = kwargs.pop("_transaction")
        old = self.copy()
        ModelItem.update(self, **kwargs)
        self._check_live_replay_timer()
        self.emit_update(old, _transaction)

    def _check_live_replay_timer(self):
        if (self.state != GameState.PLAYING or
           self._live_replay_timer.isActive() or
           self.launched_at is None):
            return

        if self.has_live_replay:
            return

        time_elapsed = time.time() - self.launched_at
        time_to_replay = max(self.LIVE_REPLAY_DELAY_SECS - time_elapsed, 0)
        self._live_replay_timer.start(time_to_replay * 1000)

    @transactional
    def _emit_live_replay(self, _transaction=None):
        if self.state != GameState.PLAYING:
            return
        self.has_live_replay = True
        _transaction.emit(self.liveReplayAvailable, self)
        self.before_replay_available.emit(self, _transaction)

    def closed(self):
        return self.state == GameState.CLOSED or self._aborted

    # Used when the server confuses us whether the game is valid anymore.
    @transactional
    def abort_game(self, _transaction=None):
        if self.closed():
            return

        old = self.copy()
        self.state = GameState.CLOSED
        self._aborted = True
        self.emit_update(old, _transaction)

    def to_dict(self):
        data = self.field_dict
        data["uid"] = self.uid
        data["state"] = data["state"].name
        data["visibility"] = data["visibility"].name
        data["command"] = "game_info"   # For compatibility
        return data

    def url(self, player_id):
        if self.state == GameState.CLOSED:
            return None
        if self.state == GameState.OPEN:
            gtype = GameUrlType.OPEN_GAME
        else:
            gtype = GameUrlType.LIVE_REPLAY

        return GameUrl(gtype, self.mapname, self.featured_mod,
                       self.uid, player_id)

    # Utility functions start here.

    def is_connected(self, name):
        return name in self._playerset

    def is_ingame(self, name):
        return (not self.closed()
                and self.is_connected(name)
                and self._playerset[name].currentGame == self)

    def to_player(self, name):
        if not self.is_connected(name):
            return None
        return self._playerset[name]

    @property
    def players(self):
        if self.teams is None:
            return []
        return [name for team in self.teams.values() for name in team]

    @property
    def observers(self):
        if self.teams is None:
            return []
        return [name for tname, team in self.teams.items()
                if tname in self.OBSERVER_TEAMS
                for name in team]

    @property
    def playing_teams(self):
        if self.teams is None:
            return {}
        return {n: t for n, t in self.teams.items()
                if n not in self.OBSERVER_TEAMS}

    @property
    def playing_players(self):
        return [name for team in self.playing_teams.values() for name in team]

    @property
    def host_player(self):
        try:
            return self._playerset[self.host]
        except KeyError:
            return None

    @transactional
    def ingame_player_added(self, player, _transaction=None):
        _transaction.emit(self.ingamePlayerAdded, self, player)

    @transactional
    def ingame_player_removed(self, player, _transaction=None):
        _transaction.emit(self.ingamePlayerRemoved, self, player)

    @property
    def average_rating(self):
        players = [name for team in self.playing_teams.values()
                   for name in team]
        players = [self.to_player(name) for name in players
                   if self.is_connected(name)]
        if not players:
            return 0
        else:
            return sum([p.rating_estimate for p in players]) / len(players)

    @property
    def mapdisplayname(self):
        if self.mapname in OFFICIAL_MAPS:
            return OFFICIAL_MAPS[self.mapname][0]

        # cut off ugly version numbers, replace "_" with space.
        pretty = self.mapname.rsplit(".v0", 1)[0]
        pretty = pretty.replace("_", " ")
        pretty = string.capwords(pretty)
        return pretty


def message_to_game_args(m):
    # FIXME - this should be fixed on the server
    if 'featured_mod' in m and m["featured_mod"] == "coop":
        if 'max_players' in m:
            m["max_players"] = 4

    if "command" in m:
        del m["command"]

    try:
        m['state'] = GameState(m['state'])
        m['visibility'] = GameVisibility(m['visibility'])
        # Server sends HTML-escaped names, which is needlessly confusing
        m['title'] = html.unescape(m['title'])
    except (KeyError, ValueError):
        return False

    return True


OFFICIAL_MAPS = {  # official Forged Alliance Maps
    "scmp_001": ["Burial Mounds", "1024x1024", 8],
    "scmp_002": ["Concord Lake", "1024x1024", 8],
    "scmp_003": ["Drake's Ravine", "1024x1024", 4],
    "scmp_004": ["Emerald Crater", "1024x1024", 4],
    "scmp_005": ["Gentleman's Reef", "2048x2048", 7],
    "scmp_006": ["Ian's Cross", "1024x1024", 4],
    "scmp_007": ["Open Palms", "512x512", 6],
    "scmp_008": ["Seraphim Glaciers", "1024x1024", 8],
    "scmp_009": ["Seton's Clutch", "1024x1024", 8],
    "scmp_010": ["Sung Island", "1024x1024", 5],
    "scmp_011": ["The Great Void", "2048x2048", 8],
    "scmp_012": ["Theta Passage", "256x256", 2],
    "scmp_013": ["Winter Duel", "256x256", 2],
    "scmp_014": ["The Bermuda Locket", "1024x1024", 8],
    "scmp_015": ["Fields Of Isis", "512x512", 4],
    "scmp_016": ["Canis River", "256x256", 2],
    "scmp_017": ["Syrtis Major", "512x512", 4],
    "scmp_018": ["Sentry Point", "256x256", 3],
    "scmp_019": ["Finn's Revenge", "512x512", 2],
    "scmp_020": ["Roanoke Abyss", "1024x1024", 6],
    "scmp_021": ["Alpha 7 Quarantine", "2048x2048", 8],
    "scmp_022": ["Artic Refuge", "512x512", 4],
    "scmp_023": ["Varga Pass", "512x512", 2],
    "scmp_024": ["Crossfire Canal", "1024x1024", 6],
    "scmp_025": ["Saltrock Colony", "512x512", 6],
    "scmp_026": ["Vya-3 Protectorate", "512x512", 4],
    "scmp_027": ["The Scar", "1024x1024", 6],
    "scmp_028": ["Hanna oasis", "2048x2048", 8],
    "scmp_029": ["Betrayal Ocean", "4096x4096", 8],
    "scmp_030": ["Frostmill Ruins", "4096x4096", 8],
    "scmp_031": ["Four-Leaf Clover", "512x512", 4],
    "scmp_032": ["The Wilderness", "512x512", 4],
    "scmp_033": ["White Fire", "512x512", 6],
    "scmp_034": ["High Noon", "512x512", 4],
    "scmp_035": ["Paradise", "512x512", 4],
    "scmp_036": ["Blasted Rock", "256x256", 4],
    "scmp_037": ["Sludge", "256x256", 3],
    "scmp_038": ["Ambush Pass", "256x256", 4],
    "scmp_039": ["Four-Corners", "256x256", 4],
    "scmp_040": ["The Ditch", "1024x1024", 6],
    "x1mp_001": ["Crag Dunes", "256x256", 2],
    "x1mp_002": ["Williamson's Bridge", "256x256", 2],
    "x1mp_003": ["Snoey Triangle", "512x512", 3],
    "x1mp_004": ["Haven Reef", "512x512", 4],
    "x1mp_005": ["The Dark Heart", "512x512", 6],
    "x1mp_006": ["Daroza's Sanctuary", "512x512", 4],
    "x1mp_007": ["Strip Mine", "1024x1024", 4],
    "x1mp_008": ["Thawing Glacier", "1024x1024", 6],
    "x1mp_009": ["Liberiam Battles", "1024x1024", 8],
    "x1mp_010": ["Shards", "2048x2048", 8],
    "x1mp_011": ["Shuriken Island", "2048x2048", 8],
    "x1mp_012": ["Debris", "4096x4096", 8],
    "x1mp_014": ["Flooded Strip Mine", "1024x1024", 4],
    "x1mp_017": ["Eye Of The Storm", "512x512", 4],
}
