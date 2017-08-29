from PyQt5.QtCore import QObject, pyqtSignal, QUrl, QUrlQuery, QTimer

from enum import Enum
from decorators import with_logger
import time


class GameState(Enum):
    OPEN = "open"
    PLAYING = "playing"
    CLOSED = "closed"


# This enum has a counterpart on the server
class GameVisibility(Enum):
    PUBLIC = "public"
    FRIENDS = "friends"


@with_logger
class Game(QObject):
    """
    Represents a game happening on the server. Updates for the game state are
    sent from the server, identified by game uid. Updates are propagated with
    signals.

    The game with a given uid starts when we receive the first game message and
    ends with some update, or is ended manually. Once the game ends, it
    shouldn't be updated or ended again. Update and game end are propagated
    with signals.
    """
    gameUpdated = pyqtSignal(object, object)
    liveReplayAvailable = pyqtSignal(object)

    connectedPlayerAdded = pyqtSignal(object, object)
    connectedPlayerRemoved = pyqtSignal(object, object)

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

        QObject.__init__(self)

        self._playerset = playerset

        self.uid = uid
        self.state = None
        self.launched_at = None
        self.num_players = None
        self.max_players = None
        self.title = None
        self.host = None
        self.mapname = None
        self.map_file_path = None
        self.teams = None
        self.featured_mod = None
        self.featured_mod_versions = None
        self.sim_mods = None
        self.password_protected = None
        self.visibility = None
        self._aborted = False

        self._live_replay_timer = QTimer()
        self._live_replay_timer.setSingleShot(True)
        self._live_replay_timer.setInterval(self.LIVE_REPLAY_DELAY_SECS * 1000)
        self._live_replay_timer.timeout.connect(self._emit_live_replay)
        self.has_live_replay = False

        self._update(state, launched_at, num_players, max_players, title,
                     host, mapname, map_file_path, teams, featured_mod,
                     featured_mod_versions, sim_mods, password_protected,
                     visibility)

    def copy(self):
        s = self
        return Game(s._playerset, s.uid, s.state, s.launched_at, s.num_players,
                    s.max_players, s.title, s.host, s.mapname, s.map_file_path,
                    s.teams, s.featured_mod, s.featured_mod_versions,
                    s.sim_mods, s.password_protected, s.visibility)

    def update(self, *args, **kwargs):
        if self._aborted:
            return
        old = self.copy()
        self._update(*args, **kwargs)
        self.gameUpdated.emit(self, old)

    def _update(self,
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
                visibility,
                uid=None,   # For convenienve
                ):

        self.launched_at = launched_at
        self.state = state
        self.num_players = num_players
        self.max_players = max_players
        self.title = title
        self.host = host
        self.mapname = mapname
        self.map_file_path = map_file_path

        # Dict of <teamname> : [list of player names]
        self.teams = teams

        # Actually a game mode like faf, coop, ladder etc.
        self.featured_mod = featured_mod

        # Featured mod versions for this game used to update FA before joining
        # TODO - investigate if this is actually necessary
        self.featured_mod_versions = featured_mod_versions

        # Dict of mod uid: mod version for each mod used by the game
        self.sim_mods = sim_mods
        self.password_protected = password_protected
        self.visibility = visibility

        self._check_live_replay_timer()

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

    def _emit_live_replay(self):
        if self.state != GameState.PLAYING:
            return
        self.has_live_replay = True
        self.liveReplayAvailable.emit(self)

    def closed(self):
        return self.state == GameState.CLOSED or self._aborted

    # Used when the server confuses us whether the game is valid anymore.
    def abort_game(self):
        if self.closed():
            return

        old = self.copy()
        self.state = GameState.CLOSED
        self._aborted = True
        self.gameUpdated.emit(self, old)

    def to_dict(self):
        return {
                "uid": self.uid,
                "state": self.state.name,
                "launched_at": self.launched_at,
                "num_players": self.num_players,
                "max_players": self.max_players,
                "title": self.title,
                "host": self.host,
                "mapname": self.mapname,
                "map_file_path": self.map_file_path,
                "teams": self.teams,
                "featured_mod": self.featured_mod,
                "featured_mod_versions": self.featured_mod_versions,
                "sim_mods": self.sim_mods,
                "password_protected": self.password_protected,
                "visibility": self.visibility.name,
                "command": "game_info"  # For compatibility
            }

    def url(self, player_id):
        if self.state == GameState.CLOSED:
            return None

        url = QUrl()
        url.setHost("lobby.faforever.com")
        query = QUrlQuery()
        query.addQueryItem("map", self.mapname)
        query.addQueryItem("mod", self.featured_mod)

        if self.state == GameState.OPEN:
            url.setScheme("fafgame")
            url.setPath("/" + str(player_id))
            query.addQueryItem("uid", str(self.uid))
        else:
            url.setScheme("faflive")
            url.setPath("/" + str(self.uid) + "/" + str(player_id) + ".SCFAreplay")

        url.setQuery(query)
        return url

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
    except (KeyError, ValueError):
        return False

    return True
