from PyQt5 import QtCore
import modvault

from fa import maps
import util
import fa.check
from model.game import Game, GameState, GameVisibility
from games.gamemodel import GameModel

import logging
logger = logging.getLogger(__name__)

FormClass, BaseClass = util.THEME.loadUiType("games/host.ui")


class GameLauncher:
    def __init__(self, playerset, me, client, game_widget):
        self._playerset = playerset
        self._me = me
        self._client = client
        self._game_widget = game_widget
        self._game_widget.launch.connect(self._launch_game)

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
        self._game_widget.setup(title, game)

        mapname = util.settings.value("fa.games/gamemap", None)
        if mapname is not None:
            self._game_widget.set_map(mapname)

        return self._game_widget.exec_()

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

        modvault.utils.setActiveMods(mods, True, False)

        self._client.host_game(title=game.title,
                               mod=game.featured_mod,
                               visibility=game.visibility.value,
                               mapname=game.mapname,
                               password=password)


class HostGameWidget(FormClass, BaseClass):
    launch = QtCore.pyqtSignal(object, object, list)

    def __init__(self, client, gameview_builder, preview_model):
        BaseClass.__init__(self, client)

        self.setupUi(self)
        self.client = client  # type: ClientWindow
        self.game = None
        self._preview_model = preview_model
        self.game_preview_logic = gameview_builder(preview_model,
                                                   self.gamePreview)
        self.mods = {}

        util.THEME.stylesheets_reloaded.connect(self.load_stylesheet)
        self.load_stylesheet()
        self.mapList.currentIndexChanged.connect(self.map_changed)
        self.hostButton.released.connect(self.hosting)
        self.titleEdit.textChanged.connect(self.update_text)
        self.passCheck.toggled.connect(self.update_pass_check)
        self.radioFriends.toggled.connect(self.update_visibility)

    def load_stylesheet(self):
        self.setStyleSheet(util.THEME.readstylesheet("client/client.css"))

    def setup(self, title, game):
        self._reset()
        self.game = game

        self.password = util.settings.value("fa.games/password", "")

        self.setWindowTitle("Hosting Game : " + title)
        self.titleEdit.setText(game.title)
        self.passEdit.setText(self.password)
        self.passCheck.setChecked(self.game.password_protected)
        self.radioFriends.setChecked(
            self.game.visibility == GameVisibility.FRIENDS)

        self._preview_model.add_game(self.game)

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

        # this makes it so you can select every non-ui_only mod
        for mod in modvault.utils.getInstalledMods():
            if mod.ui_only:
                continue
            self.mods[mod.totalname] = mod
            self.modList.addItem(mod.totalname)

        names = [mod.totalname for mod in modvault.utils.getActiveMods(uimods=False, temporary=False)]
        logger.debug("Active Mods detected: %s" % str(names))
        for name in names:
            ml = self.modList.findItems(name, QtCore.Qt.MatchExactly)
            logger.debug("found item: %s" % ml[0].text())
            if ml:
                ml[0].setSelected(True)

    def _reset(self):
        self._preview_model.clear_games()
        self.mapList.clear()
        self.mods.clear()
        self.modList.clear()


    def set_map(self, mapname):
        for i in range(self.mapList.count()):
            if self.mapList.itemData(i) == mapname:
                self.mapList.setCurrentIndex(i)
                return

    def update_text(self, text):
        self.game.update(title=text.strip())

    def update_pass_check(self, checked):
        self.game.update(password_protected=checked)

    def update_visibility(self, friends):
        self.game.update(visibility=(GameVisibility.FRIENDS if friends
                                     else GameVisibility.PUBLIC))

    def map_changed(self, index):
        mapname = self.mapList.itemData(index)
        self.game.update(mapname=mapname)

    def hosting(self):
        if len(self.game.title) == 0:
            # TODO: Feedback to the UI that the name must not be blank.
            return

        password = None
        if self.game.password_protected:
            password = self.passEdit.text()

        self.save_last_hosted_settings(password)

        modnames = [str(moditem.text()) for moditem in self.modList.selectedItems()]
        mods = [self.mods[modstr] for modstr in modnames]
        modvault.utils.setActiveMods(mods, True, False)

        self.launch.emit(self.game, password, mods)
        self.done(1)
        return

    def save_last_hosted_settings(self, password):
        util.settings.beginGroup("fa.games")
        if self.game.featured_mod != "coop":
            util.settings.setValue("gamemap", self.game.mapname)
        util.settings.setValue("gamename", self.game.title)
        util.settings.setValue("friends_only", self.radioFriends.isChecked())

        if password is not None:
            util.settings.setValue("password", self.password)
        util.settings.endGroup()


def build_launcher(playerset, me, client, view_builder, map_preview_dler):
    model = GameModel(me, map_preview_dler)
    widget = HostGameWidget(client, view_builder, model)
    launcher = GameLauncher(playerset, me, client, widget)
    return launcher
