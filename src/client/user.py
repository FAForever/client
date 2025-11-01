from __future__ import annotations

from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import MutableSet
from typing import Any
from typing import Literal
from typing import Self

from PyQt6 import QtCore
from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtBoundSignal
from PyQt6.QtCore import pyqtSignal

from src.api.models.LeagueSeasonScore import LeagueSeasonScore
from src.api.stats_api import LeagueSeasonScoreApiConnector
from src.client.connection import LobbyInfo
from src.client.connection import ServerConnection
from src.config import Settings
from src.model.chat.chatter import Chatter
from src.model.chat.chatterset import Chatterset
from src.model.modelitem import ModelItem
from src.model.modelitemset import ModelItemSet
from src.model.player import Player
from src.model.playerset import Playerset
from src.protocol.lobbyprotocol import SocialCommand


class User(QtCore.QObject):
    """
    Represents the person using the FAF Client. May have a player assigned to
    himself if he's logged in. For convenience, forwards and signals some
    underlying player information.
    """
    playerChanged = pyqtSignal(object)
    clan_changed = pyqtSignal(object, object)

    def __init__(self, playerset: Playerset) -> None:
        super().__init__()

        self._player = None
        self.id = None
        self.login = None

        self._players = playerset
        self._players.added.connect(self._on_player_change)
        self._players.removed.connect(self._on_player_change)

        self.league_api = LeagueSeasonScoreApiConnector()
        self.league_api.scores_ready.connect(self.on_league_scores)
        self._leagues: dict[str, LeagueSeasonScore] = {}

    @property
    def player(self) -> Player | None:
        return self._player

    @player.setter
    def player(self, value: Player | None) -> None:
        new = value
        old = self._player
        if old is not None:
            old.updated.disconnect(self._at_player_update)
        if new is not None:
            new.updated.connect(self._at_player_update)
        self._player = value
        self.playerChanged.emit(self._player)
        self._emit_clan_changed(new, old)

    def _at_player_update(self, new: Player, old: Player) -> None:
        if new.clan != old.clan:
            self._emit_clan_changed(new, old)

    def _emit_clan_changed(self, new_player: Player | None, old_player: Player | None) -> None:
        def pclan(p: Player | None) -> str | None:
            return None if p is None else p.clan
        self.clan_changed.emit(pclan(new_player), pclan(old_player))

    def on_login(self, login: str, id_: int) -> None:
        self.login = login
        self.id = id_
        self._update_player()
        self.league_api.get_player_scores(str(id_))

    def _update_player(self) -> None:
        if self.id is None:
            return
        new_player = self._players.get(self.id)
        if self._player is new_player:
            return
        self.player = new_player

    def _on_player_change(self, player: Player) -> None:
        if self.id is None or player.id != self.id:
            return
        self._update_player()

    def resetPlayer(self):
        self._player = None

    def is_clannie(self, pid: int | None) -> bool:
        if pid is None:
            return False
        player = self._players.get(pid)
        if player is None or self._player is None:
            return False
        if self._player.clan is None:
            return False
        return player.clan == self._player.clan

    def player_clan(self) -> str | None:
        return None if self.player is None else self.player.clan

    def on_league_scores(self, scores: list[LeagueSeasonScore]) -> None:
        for score in scores:
            assert score.season is not None
            leaderboard = score.season.leaderboard
            assert leaderboard is not None
            self._leagues[leaderboard.technical_name] = score

    def league(self, rating_type: str) -> tuple[str, str] | None:
        score = self._leagues.get(rating_type)
        if score is not None:
            assert score.subdivision is not None and score.subdivision.division is not None
            return score.subdivision.division.name, score.subdivision.name


class SetSignals(QObject):
    """
    Defined separately since QObject and MutableSet metaclasses clash.
    """
    added = pyqtSignal(object)
    removed = pyqtSignal(object)


class SignallingSet[T](MutableSet[T]):
    def __init__(self, it: Iterable[T] | None = None) -> None:
        super().__init__()
        self._set: set[T] = set(it) if it is not None else set()
        self._signals = SetSignals()

    @property
    def added(self) -> pyqtBoundSignal:
        return self._signals.added

    @property
    def removed(self) -> pyqtBoundSignal:
        return self._signals.removed

    def __contains__(self, value: object) -> bool:
        return value in self._set

    def __iter__(self) -> Iterator[T]:
        return iter(self._set)

    def __len__(self) -> int:
        return len(self._set)

    def add(self, value: T) -> None:
        if value not in self._set:
            self._set.add(value)
            self.added.emit(value)

    def discard(self, value: T) -> None:
        if value in self._set:
            self._set.discard(value)
            self.removed.emit(value)


class FriendFoeModel[T]:
    def __init__(
        self,
        friends: SignallingSet[T],
        foes: SignallingSet[T],
        chatterboxes: SignallingSet[str],
    ) -> None:
        self.friends = friends
        self.foes = foes
        self.chatterboxes = chatterboxes

    @classmethod
    def build(cls) -> Self:
        friends = SignallingSet[T]()
        foes = SignallingSet[T]()
        chatterboxes = SignallingSet[str]()
        return cls(friends, foes, chatterboxes)


class UserRelationModel:
    def __init__(
        self,
        player_relations: FriendFoeModel[int],
        irc_relations: FriendFoeModel[str],
    ) -> None:
        self.faf = player_relations
        self.irc = irc_relations

    @classmethod
    def build(cls) -> Self:
        player_relations = FriendFoeModel[int].build()
        irc_relations = FriendFoeModel[str].build()
        return cls(player_relations, irc_relations)

    def is_friend(self, id_: int | None = None, name: str | None = None) -> bool:
        if id_ not in [None, -1]:
            return id_ in self.faf.friends
        if name is not None:
            return name in self.irc.friends
        return False

    def is_foe(self, id_: int | None = None, name: str | None = None) -> bool:
        if id_ not in [None, -1]:
            return id_ in self.faf.foes
        if name is not None:
            return name in self.irc.foes
        return False

    def is_chatterbox(self, id_: int | None = None, name: str | None = None) -> bool:
        if id_ not in [None, -1]:
            return str(id_) in self.faf.chatterboxes
        if name is not None:
            return name in self.irc.chatterboxes
        return False


class IrcRelationController:
    def __init__(
        self,
        keyname: str,
        set_: SignallingSet[str],
        me: User,
        settings: type[Settings],
    ) -> None:
        self._keyname = keyname
        self._set = set_
        self._me = me
        self._me.playerChanged.connect(self._at_player_changed)
        self._settings = settings
        self._key = None
        self._at_player_changed(self._me.player)

    @classmethod
    def build(
        cls,
        keyname: str,
        set_: SignallingSet[str],
        me: User,
        settings: type[Settings],
        **kwargs: Any,
    ) -> Self:
        return cls(keyname, set_, me, settings)

    def _load(self) -> None:
        loaded: list[str]
        if self._key is None:
            loaded = []
        else:
            loaded = self._settings.get_list(self._key, default=[])
        self._set.clear()
        self._set |= set(loaded)

    def _save(self) -> None:
        if self._key is not None:
            self._settings.set(self._key, list(self._set))

    @property
    def key(self) -> str | None:
        return self._key

    @key.setter
    def key(self, value: str | None) -> None:
        self._key = value
        self._load()

    def _at_player_changed(self, player: Player | None) -> None:
        self.key = self._irc_key(player)

    def _irc_key(self, player: Player | None) -> str | None:
        if player is None:
            return None
        return f"chat.{self._keyname}/{player.id}"

    def add(self, item: str | int) -> None:
        self._set.add(str(item))
        self._save()

    def remove(self, item: str | int) -> None:
        self._set.discard(str(item))
        self._save()


class FafRelationController:
    def __init__(
        self,
        msg_in: Literal["friends", "foes"],
        msg_out: Literal["friend", "foe"],
        set_: SignallingSet[int],
        lobby_info: LobbyInfo,
        lobby_connection: ServerConnection,
    ) -> None:
        self._msg_in = msg_in
        self._msg_out = msg_out
        self._set = set_
        self._lobby_info = lobby_info
        self._lobby_info.social.connect(self._handle_social)
        self._lobby_connection = lobby_connection

    @classmethod
    def build(
        cls,
        msg_in: Literal["friends", "foes"],
        msg_out: Literal["friend", "foe"],
        set_: SignallingSet[int],
        lobby_info: LobbyInfo,
        lobby_connection: ServerConnection,
        **kwargs: Any,
    ) -> Self:
        return cls(msg_in, msg_out, set_, lobby_info, lobby_connection)

    def _handle_social(self, message: SocialCommand) -> None:
        data = message.get(self._msg_in)
        if data is None:
            return
        self._set.clear()
        self._set |= {int(pid) for pid in data}

    def _send_message(self, action: str, pid: int) -> None:
        self._lobby_connection.send({
            "command": action,
            self._msg_out: pid,
        })

    def add(self, pid: str | int) -> None:
        # FIXME: this method should only accept ints, but it accepts strs too
        # to be consistent with IrcFriendFoeController's method
        # (see _handle_social in playercontextmenu)
        assert isinstance(pid, int)
        if pid not in self._set:
            self._send_message("social_add", pid)
            self._set.add(pid)

    def remove(self, pid: str | int) -> None:
        assert isinstance(pid, int)  # FIXME
        if pid in self._set:
            self._send_message("social_remove", pid)
            self._set.remove(pid)


class IrcFriendFoeController:
    def __init__(
        self,
        friends: IrcRelationController,
        foes: IrcRelationController,
        chatterboxes: IrcRelationController,
    ) -> None:
        self.friends = friends
        self.foes = foes
        self.chatterboxes = chatterboxes

    @classmethod
    def build(cls, irc_relations: FriendFoeModel[str], **kwargs: Any) -> Self:
        friends = IrcRelationController.build(
            "irc_friends", irc_relations.friends, **kwargs,
        )
        foes = IrcRelationController.build(
            "irc_foes", irc_relations.foes, **kwargs,
        )
        chatterboxes = IrcRelationController.build(
            "irc_chatterboxes", irc_relations.chatterboxes, **kwargs,
        )
        return cls(friends, foes, chatterboxes)


class FafFriendFoeController:
    def __init__(
        self,
        friends: FafRelationController,
        foes: FafRelationController,
        chatterboxes: IrcRelationController,
    ) -> None:
        self.friends = friends
        self.foes = foes
        self.chatterboxes = chatterboxes

    @classmethod
    def build(cls, faf_relations: FriendFoeModel[int], **kwargs: Any) -> Self:
        friends = FafRelationController.build(
            "friends", "friend", faf_relations.friends, **kwargs,
        )
        foes = FafRelationController.build(
            "foes", "foe", faf_relations.foes, **kwargs,
        )
        chatterboxes = IrcRelationController.build(
            "chatterboxes", faf_relations.chatterboxes, **kwargs,
        )
        return cls(friends, foes, chatterboxes)


class UserRelationController:
    def __init__(
        self,
        player_controller: FafFriendFoeController,
        irc_controller: IrcFriendFoeController,
    ) -> None:
        self.faf = player_controller
        self.irc = irc_controller

    @classmethod
    def build(cls, user_relations: UserRelationModel, **kwargs: Any) -> Self:
        player_controller = FafFriendFoeController.build(user_relations.faf, **kwargs)
        irc_controller = IrcFriendFoeController.build(user_relations.irc, **kwargs)
        return cls(player_controller, irc_controller)


class UserRelationship(QObject):
    """
    Used to notify about relationship changes of a particular user.
    For now we need it only to update views, so a single 'update' signal is
    enough.
    """
    updated = pyqtSignal()


class RelationshipTracker[KT, VT: ModelItem](QObject):
    """
    This class listens to relationship change events and distributes them among
    objects corresponding to particular chatters / players. This is done so
    that a single relationship change does not trigger 1k chatter view slots.
    It also reports any updates to any of the items.
    """
    updated = pyqtSignal(object)

    def __init__(self, item_set: ModelItemSet[KT, VT]) -> None:
        QObject.__init__(self)
        self._item_set = item_set
        self._item_set.removed.connect(self._at_item_removed)
        self._trackers: dict[KT, UserRelationship] = {}

    def add_tracker(self, key: KT, /) -> None:
        self._trackers[key] = self._create_tracker(key)

    # Since users of this class might listen to addition and removal of
    # chatters or players and the add / remove signal slots are
    # executed in an unspecified order, we can't just create trackers
    # at an add signal - we have to do it on-demand.
    def __getitem__(self, key: KT, /) -> UserRelationship:
        if key not in self._trackers:
            if key not in self._item_set:
                raise KeyError
            self.add_tracker(key)
        return self._trackers[key]

    def _create_tracker(self, key: KT, /) -> UserRelationship:
        return UserRelationship()

    def _at_item_removed(self, item: VT, /) -> None:
        if item.id_key in self._trackers:
            del self._trackers[item.id_key]

    def _at_relation_updated(self, key: KT, /) -> None:
        tracker = self._trackers.get(key, None)
        if tracker is None:
            return
        tracker.updated.emit()
        self.updated.emit(key)


class FriendFoeTracker[KT, VT: ModelItem](RelationshipTracker[KT, VT]):
    def __init__(self, friendfoes: FriendFoeModel[KT], item_set: ModelItemSet[KT, VT]) -> None:
        super().__init__(item_set)
        self._friendfoes = friendfoes
        for s in [
            friendfoes.friends,
            friendfoes.foes,
            friendfoes.chatterboxes,
        ]:
            for sig in [s.added, s.removed]:
                sig.connect(self._at_relation_updated)


class UserRelationTrackers:
    def __init__(
        self,
        chatter_tracker: FriendFoeTracker[str, Chatter],
        player_tracker: FriendFoeTracker[int, Player],
    ) -> None:
        self.chatters = chatter_tracker
        self.players = player_tracker

    @classmethod
    def build(
        cls,
        relation_model: UserRelationModel,
        playerset: Playerset,
        chatterset: Chatterset,
    ) -> Self:
        chatter_tracker = FriendFoeTracker(relation_model.irc, chatterset)
        player_tracker = FriendFoeTracker(relation_model.faf, playerset)
        return cls(chatter_tracker, player_tracker)


class UserRelations:
    def __init__(
        self,
        model: UserRelationModel,
        controller: UserRelationController,
        trackers: UserRelationTrackers,
    ) -> None:
        self.model = model
        self.controller = controller
        self.trackers = trackers
