from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSignal
from collections.abc import MutableSet


class User(QtCore.QObject):
    """
    Represents the person using the FAF Client. May have a player assigned to
    himself if he's logged in. For convenience, forwards and signals some
    underlying player information.
    """
    playerChanged = pyqtSignal(object)
    clan_changed = pyqtSignal(object, object)

    def __init__(self, playerset):
        QtCore.QObject.__init__(self)

        self._player = None
        self.id = None
        self.login = None

        self._players = playerset
        self._players.added.connect(self._on_player_change)
        self._players.removed.connect(self._on_player_change)

        self.relations = None   # FIXME - circular me -> rels -> me dep

    @property
    def player(self):
        return self._player

    @player.setter
    def player(self, value):
        new = value
        old = self._player
        if old is not None:
            old.updated.disconnect(self._at_player_update)
        if new is not None:
            new.updated.connect(self._at_player_update)
        self._player = value
        self.playerChanged.emit(self._player)
        self._emit_clan_changed(new, old)

    def _at_player_update(self, new, old):
        if new.clan != old.clan:
            self._emit_clan_changed(new, old)

    def _emit_clan_changed(self, new_player, old_player):
        def pclan(p):
            return None if p is None else p.clan
        self.clan_changed.emit(pclan(new_player), pclan(old_player))

    def onLogin(self, login, id_):
        self.login = login
        self.id = id_
        self._update_player()

    def _update_player(self):
        new_player = self._players.get(self.id, None)
        if self._player is new_player:
            return
        self.player = new_player

    def _on_player_change(self, player):
        if self.id is None or player.id != self.id:
            return
        self._update_player()

    def resetPlayer(self):
        self._player = None

    def is_clannie(self, pid):
        if pid is None:
            return False
        player = self._players.get(pid, None)
        if player is None or self._player is None:
            return False
        return player.clan == self._player.clan

    def player_clan(self):
        return None if self.player is None else self.player.clan


class SetSignals(QObject):
    """
    Defined separately since QObject and MutableSet metaclasses clash.
    """
    added = pyqtSignal(object)
    removed = pyqtSignal(object)

    def __init__(self):
        QObject.__init__(self)


class SignallingSet(MutableSet):
    def __init__(self):
        MutableSet.__init__(self)
        self._set = set()
        self._signals = SetSignals()

    @property
    def added(self):
        return self._signals.added

    @property
    def removed(self):
        return self._signals.removed

    def __contains__(self, value):
        return value in self._set

    def __iter__(self):
        return iter(self._set)

    def __len__(self):
        return len(self._set)

    def add(self, value):
        if value not in self._set:
            self._set.add(value)
            self.added.emit(value)

    def discard(self, value):
        if value in self._set:
            self._set.discard(value)
            self.removed.emit(value)


class FriendFoeModel:
    def __init__(self, friends, foes):
        self.friends = friends
        self.foes = foes

    @classmethod
    def build(cls, **kwargs):
        friends = SignallingSet()
        foes = SignallingSet()
        return cls(friends, foes)


class UserRelationModel:
    def __init__(self, player_relations, irc_relations):
        self.faf = player_relations
        self.irc = irc_relations

    @classmethod
    def build(cls, **kwargs):
        player_relations = FriendFoeModel.build()
        irc_relations = FriendFoeModel.build()
        return cls(player_relations, irc_relations)

    def is_friend(self, id_=None, name=None):
        if id_ not in [None, -1]:
            return id_ in self.faf.friends
        if name is not None:
            return name in self.irc.friends
        return False

    def is_foe(self, id_=None, name=None):
        if id_ not in [None, -1]:
            return id_ in self.faf.foes
        if name is not None:
            return name in self.irc.foes
        return False


class IrcRelationController:
    def __init__(self, keyname, set_, me, settings):
        self._keyname = keyname
        self._set = set_
        self._me = me
        self._me.playerChanged.connect(self._at_player_changed)
        self._settings = settings
        self._key = None
        self._at_player_changed(self._me.player)

    @classmethod
    def build(cls, keyname, set_, me, settings, **kwargs):
        return cls(keyname, set_, me, settings)

    def _load(self):
        if self._key is None:
            loaded = []
        else:
            loaded = self._settings.get(self._key, [])
        self._set.clear()
        self._set |= loaded

    def _save(self):
        if self._key is not None:
            self._settings.set(self._key, list(self._set))

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, value):
        self._key = value
        self._load()

    def _at_player_changed(self, player):
        self.key = self._irc_key(player)

    def _irc_key(self, player):
        if player is None:
            return None
        return "chat.irc_{}/{}".format(self._keyname, player.id)

    def add(self, item):
        self._set.add(item)
        self._save()

    def remove(self, item):
        self._set.discard(item)
        self._save()


class FafRelationController:
    def __init__(self, msg_in, msg_out, set_, lobby_info, lobby_connection):
        self._msg_in = msg_in
        self._msg_out = msg_out
        self._set = set_
        self._lobby_info = lobby_info
        self._lobby_info.social.connect(self._handle_social)
        self._lobby_connection = lobby_connection

    @classmethod
    def build(cls, msg_in, msg_out, set_, lobby_info, lobby_connection,
              **kwargs):
        return cls(msg_in, msg_out, set_, lobby_info, lobby_connection)

    def _handle_social(self, message):
        data = message.get(self._msg_in, None)
        if data is None:
            return
        self._set.clear()
        self._set |= (int(pid) for pid in data)

    def _send_message(self, action, pid):
        self._lobby_connection.send({
            "command": action,
            self._msg_out: pid
        })

    def add(self, pid):
        if pid not in self._set:
            self._send_message("social_add", pid)
            self._set.add(pid)

    def remove(self, pid):
        if pid in self._set:
            self._send_message("social_remove", pid)
            self._set.remove(pid)


class IrcFriendFoeController:
    def __init__(self, friends, foes):
        self.friends = friends
        self.foes = foes

    @classmethod
    def build(cls, irc_relations, **kwargs):
        friends = IrcRelationController.build("friends", irc_relations.friends,
                                              **kwargs)
        foes = IrcRelationController.build("foes", irc_relations.foes,
                                           **kwargs)
        return cls(friends, foes)


class FafFriendFoeController:
    def __init__(self, friends, foes):
        self.friends = friends
        self.foes = foes

    @classmethod
    def build(cls, faf_relations, **kwargs):
        friends = FafRelationController.build("friends", "friend",
                                              faf_relations.friends, **kwargs)
        foes = FafRelationController.build("foes", "foe",
                                           faf_relations.foes, **kwargs)
        return cls(friends, foes)


class UserRelationController:
    def __init__(self, player_controller, irc_controller):
        self.faf = player_controller
        self.irc = irc_controller

    @classmethod
    def build(cls, user_relations, **kwargs):
        player_controller = FafFriendFoeController.build(user_relations.faf,
                                                         **kwargs)
        irc_controller = IrcFriendFoeController.build(user_relations.irc,
                                                      **kwargs)
        return cls(player_controller, irc_controller)


class UserRelationship(QObject):
    """
    Used to notify about relationship changes of a particular user.
    For now we need it only to update views, so a single 'update' signal is
    enough.
    """
    updated = pyqtSignal()

    def __init__(self):
        QObject.__init__(self)


class RelationshipTracker(QObject):
    """
    This class listens to relationship change events and distributes them among
    objects corresponding to particular chatters / players. This is done so
    that a single relationship change does not trigger 1k chatter view slots.
    It also reports any updates to any of the items.
    """
    updated = pyqtSignal(object)

    def __init__(self, item_set):
        QObject.__init__(self)
        self._item_set = item_set
        self._item_set.removed.connect(self._at_item_removed)
        self._trackers = {}

    # Since users of this class might listen to addition and removal of
    # chatters or players and the add / remove signal slots are
    # executed in an unspecified order, we can't just create trackers
    # at an add signal - we have to do it on-demand.
    def __getitem__(self, key):
        if key not in self._trackers:
            if key not in self._item_set:
                raise KeyError
            self._trackers[key] = self._create_tracker(key)
        return self._trackers[key]

    def _create_tracker(self, key):
        return UserRelationship()

    def _at_item_removed(self, item):
        if item.id_key in self._trackers:
            del self._trackers[item.id_key]

    def _at_relation_updated(self, key):
        tracker = self._trackers.get(key, None)
        if tracker is None:
            return
        tracker.updated.emit()
        self.updated.emit(key)


class FriendFoeTracker(RelationshipTracker):
    def __init__(self, friendfoes, item_set):
        RelationshipTracker.__init__(self, item_set)
        self._friendfoes = friendfoes
        for s in [friendfoes.friends, friendfoes.foes]:
            for sig in [s.added, s.removed]:
                sig.connect(self._at_relation_updated)

    @classmethod
    def build_for_players(cls, friendfoes, playerset, **kwargs):
        return cls(friendfoes, playerset)

    @classmethod
    def build_for_chatters(cls, friendfoes, chatterset, **kwargs):
        return cls(friendfoes, chatterset)


class UserRelationTrackers:
    def __init__(self, chatter_tracker, player_tracker):
        self.chatters = chatter_tracker
        self.players = player_tracker

    @classmethod
    def build(cls, relation_model, **kwargs):
        chatter_tracker = FriendFoeTracker.build_for_chatters(
                relation_model.irc, **kwargs)
        player_tracker = FriendFoeTracker.build_for_players(
                relation_model.faf, **kwargs)
        return cls(chatter_tracker, player_tracker)


class UserRelations:
    def __init__(self, model, controller, trackers):
        self.model = model
        self.controller = controller
        self.trackers = trackers
