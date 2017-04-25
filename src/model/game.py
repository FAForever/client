from PyQt5.QtCore import QObject, pyqtSignal

from enum import Enum
from decorators import with_logger


class GameState(Enum):
    OPEN = "open"
    PLAYING = "playing"
    CLOSED = "closed"

# This enum has a counterpart on the server
class GameVisibility(Enum):
    PUBLIC = "public"
    FRIENDS = "friends"

# For when we get an inconsistent game update.
class BadUpdateException(Exception):
    pass

"""
Represents a game happening on the server. Updates for the game state are sent
from the server, identified by game uid. Updates are propagated with signals.

The game with a given uid starts when we receive the first game message and
ends with some update, or is ended manually. Once the game ends, it can't be
updated or ended again. Update and game end are propagated with signals.

If an update is malformed / forbidden, an exception is thrown.
"""
@with_logger
class Game(QObject):

    gameUpdated = pyqtSignal(object)
    gameClosed = pyqtSignal(object)
    newState = pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        QObject.__init__(self)

        try:
            self.uid = (lambda uid, *a, **kw: uid) (*args, **kwargs) # Extract uid from args
        except TypeError as e:
            raise BadUpdateException(e.args[0])

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

        self.update(*args, **kwargs)

    def update(self, *args, **kwargs):
        try:
            self._update(*args, **kwargs)
        except TypeError as e:
            raise BadUpdateException(e.args[0])

    def _update(self,
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
        visibility,
        command = None,    # Ignored, for convenience since server puts this in the game dict
        ):

        if self.closed():
            raise BadUpdateException("Cannot update a closed game {}!".format(self.uid))

        if self.uid != uid:
            raise BadUpdateException("Trying to update game {} with mismatching uid {}"
                                     .format(self.uid, uid))

        try:
            state = GameState(state)
        except ValueError:
            raise BadUpdateException("Unknown game state {} for game {}"
                                     .format(state, self.uid))

        try:
            visibility = GameVisibility(visibility)
        except ValueError:
            raise BadUpdateException("Unknown game {} visibility {}"
                                     .format(self.uid, visibility))

        if self.launched_at is not None and self.launched_at != launched_at:
            self._logger.warn("Overwriting launch time for game {}".format(self.uid))

        oldstate = self.state
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

        self.gameUpdated.emit(self)
        if self.state != oldstate:
            self.newState.emit(self)
        if self.closed():
            self.gameClosed.emit(self)

    def closed(self):
        return self.state == GameState.CLOSED or self._aborted

    # Used when the server confuses us whether the game is valid anymore.
    def abort_game(self):
        if not self.closed():
            self._aborted = True
            self.gameClosed.emit(self)

    def to_dict(self):
        return {
                "uid": self.uid,
                "state": self.state,
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
                "visibility": self.visibility,
                "command": "game_info" # For compatibility
            }
