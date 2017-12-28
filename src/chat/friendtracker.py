from PyQt5.QtCore import QObject, pyqtSignal
from enum import Enum
from model.game import GameState

class FriendEvents(Enum):
    HOSTING_GAME = 1
    JOINED_GAME = 2
    REPLAY_AVAILABLE = 3


class OnlineFriendsTracker(QObject):
    """
    Keeps track of current online friends. Notifies about added or removed
    friends, no matter if it happens through (dis)connecting or through
    the user adding or removing friends.
    """
    friendAdded = pyqtSignal(object)
    friendRemoved = pyqtSignal(object)

    def __init__(self, me, playerset):
        QObject.__init__(self)
        self.friends = set()
        self._me = me
        self._playerset = playerset

        self._me.relationsUpdated.connect(self._update_friends)
        self._playerset.playerAdded.connect(self._add_or_update_player)
        self._playerset.playerRemoved.connect(self._remove_player)

        for player in self._playerset:
            self._add_or_update_player(player)

    def _is_friend(self, player):
        return self._me.isFriend(player.id)

    def _add_friend(self, player):
        if player in self.friends:
            return
        self.friends.add(player)
        self.friendAdded.emit(player)

    def _remove_friend(self, player):
        if player not in self.friends:
            return
        self.friends.remove(player)
        self.friendRemoved.emit(player)

    def _add_or_update_player(self, player):
        if self._is_friend(player):
            self._add_friend(player)
        else:
            self._remove_friend(player)

    def _remove_player(self, player):
        self._remove_friend(player)

    def _update_friends(self, player_ids):
        for pid in player_ids:
            try:
                player = self._playerset[pid]
            except KeyError:
                continue
            self._add_or_update_player(player)


class FriendEventTracker(QObject):
    """
    Tracks and notifies about interesting events of a single friend player.
    """
    friendEvent = pyqtSignal(object, object)

    def __init__(self, friend):
        QObject.__init__(self)
        self._friend = friend
        self._friend_game = None
        friend.newCurrentGame.connect(self._on_new_friend_game)
        self._reconnect_game_signals()

    def _on_new_friend_game(self):
        self._reconnect_game_signals()
        self._check_game_joining_event()

    def _reconnect_game_signals(self):
        old_game = self._friend_game
        if old_game is not None:
            old_game.liveReplayAvailable.disconnect(
                    self._check_game_replay_event)

        new_game = self._friend.currentGame
        self._friend_game = new_game
        if new_game is not None:
            new_game.liveReplayAvailable.connect(
                    self._check_game_replay_event)

    def _check_game_joining_event(self):
        if self._friend_game is None:
            return
        if self._friend_game.state == GameState.OPEN:
            if self._friend_game.host == self._friend.login:
                self.friendEvent.emit(self._friend, FriendEvents.HOSTING_GAME)
            else:
                self.friendEvent.emit(self._friend, FriendEvents.JOINED_GAME)

    def _check_game_replay_event(self):
        if self._friend_game is None:
            return
        if not self._friend_game.has_live_replay:
            return
        self.friendEvent.emit(self._friend, FriendEvents.REPLAY_AVAILABLE)

    def report_all_events(self):
        self._check_game_joining_event()
        self._check_game_replay_event()


class FriendsEventTracker(QObject):
    """
    Forwards notifications about all online friend players.
    FIXME: we duplicate all friend tracker signals here, is there a more
    elegant way? Maybe an enum and a single signal?
    """
    friendEvent = pyqtSignal(object, object)

    def __init__(self, online_friend_tracker):
        QObject.__init__(self)
        self._online_friend_tracker = online_friend_tracker
        self._friend_event_trackers = {}

        self._online_friend_tracker.friendAdded.connect(self._add_friend)
        self._online_friend_tracker.friendRemoved.connect(self._remove_friend)

        for friend in self._online_friend_tracker.friends:
            self._add_friend(friend)

    def _add_friend(self, friend):
        tracker = FriendEventTracker(friend)
        tracker.friendEvent.connect(self.friendEvent.emit)
        self._friend_event_trackers[friend.id] = tracker

        # No risk of reporting an event twice - either it didn't happen yet
        # so it won't be reported here, or it happened already so it wasn't
        # tracked
        tracker.report_all_events()

    def _remove_friend(self, friend):
        try:
            # Signals get disconnected automatically since tracker is
            # no longer referenced.
            del self._friend_event_trackers[friend.id]
        except KeyError:
            pass


def build_friends_tracker(me, playerset):
    online_friend_tracker = OnlineFriendsTracker(me, playerset)
    friends_event_tracker = FriendsEventTracker(online_friend_tracker)
    return friends_event_tracker
