from PyQt5 import QtCore
from games.gameitem import GameItemWidget, GameItemDelegate
import modvault

from fa import maps
import util
import fa.check
from model.game import Game, GameState, GameVisibility

import logging
logger = logging.getLogger(__name__)

FormClass, BaseClass = util.THEME.loadUiType("games/host.ui")


class GameLauncher:
    def __init__(self, playerset, me, client):
        self._playerset = playerset
        self._me = me
        self._client = client

    def _build_hosted_game(self, main_mod, mapname=None):
        if mapname is None:
            mapname = util.settings.value("fa.games/gamemap", "scmp_007")

        if self._me.player is not None:
            host = self._me.player.login
        else:
            host = "Unknown"

        title = util.settings.value("fa.games/gamename", host + "'s game")
        friends_only = util.settings.value("friends_only", False, type=bool)

        return Game(
            playerset=self._playerset,
            uid=0,  # Mock
            state=GameState.OPEN,   # Mock
            launched_at=None,
            num_players=1,
            max_players=12,
            title=title,
            host=host,
            mapname=mapname,
            map_file_path="",   # Mock
            teams={1: [host]},
            featured_mod=main_mod,
            featured_mod_versions={},
            sim_mods={},
            password_protected=False,   # Filled in later
            visibility=(GameVisibility.FRIENDS if friends_only
                        else GameVisibility.PUBLIC)
            )

    def host_game(self, title, main_mod, mapname=None):
        game = self._build_hosted_game(main_mod, mapname)
        host_widget = HostgameWidget(self._client, title, game)
        host_widget.launch.connect(self._launch_game)
        return host_widget.exec_()

    def _launch_game(self, game, password, mods):
        # Make sure the binaries are all up to date, and abort if the update fails or is cancelled.
        if not fa.check.game(self._client):
            return

        # Ensure all mods are up-to-date, and abort if the update process fails.
        if not fa.check.check(game.featured_mod):
            return
        if (game.featured_mod == "coop"
           and not fa.check.map_(game.mapname, force=True)):
            return

        modvault.setActiveMods(mods, True, False)

        self._client.host_game(title=game.title,
                               mod=game.featured_mod,
                               visibility=game.visibility.value,
                               mapname=game.mapname,
                               password=password)


class HostgameWidget(FormClass, BaseClass):
    launch = QtCore.pyqtSignal(object, str, list)

    def __init__(self, client, title, game):
        BaseClass.__init__(self, client)

        self.setupUi(self)
        self.client = client
        self.game = game

        self.setStyleSheet(self.client.styleSheet())
        self.password = util.settings.value("fa.games/password", "")

        self.setWindowTitle("Hosting Game : " + title)
        self.titleEdit.setText(game.title)
        self.passEdit.setText(self.password)
        self.gameitem = GameItemWidget(self)
        self.gamePreview.setItemDelegate(GameItemDelegate(self))
        self.gamePreview.addItem(self.gameitem)

        self.game.password_protected = self.passCheck.isChecked()

        w = self.gameitem
        w.setHidden(True)
        w.title = self.game.title
        w.host = self.client.login
        w.modName = self.game.featured_mod
        w.mapName = self.game.mapname
        w.players = self.game.num_players
        w.maxPlayers = self.game.max_players
        me = self.client.me.player
        w.teamsToTooltip([[me]])

        w.updateText()
        w.updateIcon()
        w.updateTooltip()
        w.setHidden(False)

        i = 0
        index = 0
        if game.featured_mod != "coop":
            allmaps = {}
            for map_ in list(maps.maps.keys()) + maps.getUserMaps():
                allmaps[map_] = maps.getDisplayName(map_)
            for (map_, name) in sorted(iter(allmaps.items()), key=lambda x: x[1]):
                if map_ == game.mapname:
                    index = i
                self.mapList.addItem(name, map_)
                i = i + 1
            self.mapList.setCurrentIndex(index)
        else:
            self.mapList.hide()

        self.mods = {}
        # this makes it so you can select every non-ui_only mod
        for mod in modvault.getInstalledMods():
            if mod.ui_only:
                continue
            self.mods[mod.totalname] = mod
            self.modList.addItem(mod.totalname)

        names = [mod.totalname for mod in modvault.getActiveMods(uimods=False, temporary=False)]
        logger.debug("Active Mods detected: %s" % str(names))
        for name in names:
            l = self.modList.findItems(name, QtCore.Qt.MatchExactly)
            logger.debug("found item: %s" % l[0].text())
            if l:
                l[0].setSelected(True)

        self.radioFriends.setChecked(
            self.game.visibility == GameVisibility.FRIENDS)

        self.mapList.currentIndexChanged.connect(self.mapChanged)
        self.hostButton.released.connect(self.hosting)
        self.titleEdit.textChanged.connect(self.updateText)

    def updateText(self, text):
        self.gameitem.title = text
        self.gameitem.updateText()
        self.game.title = text

    def hosting(self):
        name = self.titleEdit.text().strip()
        if len(name) == 0:
            # TODO: Feedback to the UI that the name must not be blank.
            return
        self.game.title = name

        self.game.visibility = (
            GameVisibility.FRIENDS if self.radioFriends.isChecked()
            else GameVisibility.PUBLIC)

        password = None
        if self.passCheck.isChecked():
            self.game.password_protected = True
            password = self.passEdit.text()

        self.save_last_hosted_settings(password)

        modnames = [str(moditem.text()) for moditem in self.modList.selectedItems()]
        mods = [self.mods[modstr] for modstr in modnames]
        modvault.setActiveMods(mods, True, False)

        self.launch.emit(self.game, password, mods)
        self.done(1)
        return

    def mapChanged(self, index):
        mapname = self.mapList.itemData(index)
        self.game.mapname = mapname

        self.gameitem.mapName = mapname
        self.gameitem.updateText()
        self.gameitem.updateIcon()

    def save_last_hosted_settings(self, password):
        util.settings.beginGroup("fa.games")
        if self.game.featured_mod != "coop":
            util.settings.setValue("gamemap", self.game.mapname)
        util.settings.setValue("gamename", self.game.title)
        util.settings.setValue("friends_only", self.radioFriends.isChecked())

        if password is not None:
            util.settings.setValue("password", self.password)
        util.settings.endGroup()
