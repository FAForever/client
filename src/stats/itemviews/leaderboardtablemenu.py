from enum import Enum

from PyQt5 import QtWidgets


class LeaderboardTableMenuItems(Enum):
    VIEW_ALIASES = "View aliases"
    VIEW_REPLAYS = "View Replays in Vault"
    ADD_FRIEND = "Add friend"
    ADD_FOE = "Add foe"
    REMOVE_FRIEND = "Remove friend"
    REMOVE_FOE = "Remove foe"
    COPY_USERNAME = "Copy username"


class LeaderboardTableMenu:
    def __init__(self, parent, client, leaderboardName):
        self.parent = parent
        self.client = client
        self.leaderboardName = leaderboardName

    @classmethod
    def build(cls, parent, client, leaderboardName):
        return cls(parent, client, leaderboardName)

    def actions(self, name, uid):
        yield list(self.usernameActions())
        yield list(self.playerActions())

        if self.client.me.player is None:
            return

        is_me = self.client.me.id == uid
        yield list(self.friendActions(name, uid, is_me))

    def usernameActions(self):
        yield LeaderboardTableMenuItems.COPY_USERNAME
        yield LeaderboardTableMenuItems.VIEW_ALIASES

    def playerActions(self):
        yield LeaderboardTableMenuItems.VIEW_REPLAYS

    def friendActions(self, name, uid, is_me):
        if is_me:
            return

        if self.client.me.relations.model.is_friend(uid, name):
            yield LeaderboardTableMenuItems.REMOVE_FRIEND
        elif self.client.me.relations.model.is_foe(uid, name):
            yield LeaderboardTableMenuItems.REMOVE_FOE
        else:
            yield LeaderboardTableMenuItems.ADD_FRIEND
            yield LeaderboardTableMenuItems.ADD_FOE

    def getMenu(self, name, uid):
        menu = QtWidgets.QMenu(self.parent)

        def addEntry(item):
            action = QtWidgets.QAction(item.value, menu)
            action.triggered.connect(self.handler(name, uid, item))
            menu.addAction(action)

        first = True
        for category in self.actions(name, uid):
            if not category:
                continue
            if not first:
                menu.addSeparator()
            for item in category:
                addEntry(item)
            first = False
        return menu

    def handler(self, name, uid, kind):
        Items = LeaderboardTableMenuItems
        if kind == Items.COPY_USERNAME:
            return lambda: self.copyUsername(name)
        elif kind == Items.VIEW_ALIASES:
            return lambda: self.viewAliases(name)
        elif kind == Items.VIEW_REPLAYS:
            return lambda: self.viewReplays(name)
        elif kind in [
            Items.ADD_FRIEND, Items.ADD_FOE, Items.REMOVE_FRIEND,
            Items.REMOVE_FOE,
        ]:
            return lambda: self.handleFriends(uid, kind)

    def copyUsername(self, name):
        QtWidgets.QApplication.clipboard().setText(name)

    def viewAliases(self, name):
        self.client._alias_viewer.view_aliases(name)

    def viewReplays(self, name):
        self.client.view_replays(name, self.leaderboardName)

    def handleFriends(self, uid, kind):
        ctl = self.client.me.relations.controller.faf

        Items = LeaderboardTableMenuItems
        if kind == Items.ADD_FRIEND:
            ctl.friends.add(uid)
        elif kind == Items.REMOVE_FRIEND:
            ctl.friends.remove(uid)
        if kind == Items.ADD_FOE:
            ctl.foes.add(uid)
        elif kind == Items.REMOVE_FOE:
            ctl.foes.remove(uid)
