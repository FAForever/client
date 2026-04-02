import logging
import os
import random
import re
import time
from collections.abc import Iterable
from functools import partial
from typing import TYPE_CHECKING
from typing import cast

from PyQt6 import QtCore
from PyQt6.QtCore import QThread
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QBrush
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QIcon
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QAbstractButton
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QListWidgetItem

from src import fa
from src import util
from src.api.models.MapVersion import MapSize
from src.client.user import User
from src.config import Settings
from src.fa import maps
from src.fa.maps_.preview import create_largest_preview
from src.fa.maps_.previewdialog import MapPreviewDialog
from src.games.host_ui import HostGameDialogUi
from src.games.mapgenoptionsdialog import MapGenDialog
from src.model.game import Game
from src.model.game import GameState
from src.model.game import GameType
from src.model.game import GameVisibility
from src.model.playerset import Playerset
from src.qt.utils import block_signals
from src.vaults.modvault.utils import ModInfo
from src.vaults.modvault.utils import getActiveMods
from src.vaults.modvault.utils import getInstalledMods
from src.vaults.modvault.utils import setActiveMods

if TYPE_CHECKING:
    from src.client._clientwindow import ClientWindow


logger = logging.getLogger(__name__)


class GameLauncher:
    def __init__(
            self,
            playerset: Playerset,
            me: User,
            client: ClientWindow,
            game_widget: HostGameWidget,
    ) -> None:
        self._playerset = playerset
        self._me = me
        self._client = client
        self._game_widget = game_widget
        self._game_widget.launch.connect(self._launch_game)

    def _build_hosted_game(self, main_mod: str, mapname: str | None = None) -> Game:
        if mapname is None:
            mapname = Settings.get("fa.games/gamemap", "scmp_007")

        if self._me.player is not None:
            host = self._me.player.login
        else:
            host = "Unknown"

        with Settings.group("fa.games") as g:
            title = g.value("gamename", f"{host}'s game")
            friends_only = g.value("friends_only", False, type=bool)
            enforce_rating = g.value("enforce_rating_range", False, type=bool)
            rating_min = g.value("rating_min", None, type=int)
            rating_max = g.value("rating_max", None, type=int)

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
            sim_mods={},
            password_protected=False,   # Filled in later
            visibility=(
                GameVisibility.FRIENDS
                if friends_only
                else GameVisibility.PUBLIC
            ),
            hosted_at=str(time.time()),
            game_type=GameType.CUSTOM.value,
            enforce_rating_range=enforce_rating,
            rating_min=rating_min,
            rating_max=rating_max,
        )

    def host_game(self, title: str, main_mod: str, mapname: str | None = None) -> int:
        game = self._build_hosted_game(main_mod, mapname)
        self._game_widget.setup(title, game)

        mapname = Settings.get("fa.games/gamemap", None)
        if mapname is not None:
            self._game_widget.set_map(mapname)

        return self._game_widget.exec()

    def _launch_game(self, game: Game, password: str) -> None:
        # Make sure the binaries and mods are all up to date,
        # and abort if the update fails or is cancelled.
        if not fa.check.check(game.featured_mod):
            return
        if (
            game.featured_mod == "coop"
            and not fa.check.map_(game.mapname, force=True)
        ):
            return

        self._client.host_game(
            title=game.title,
            mod=game.featured_mod,
            visibility=game.visibility.value,
            mapname=game.mapname,
            password=password,
            enforce_rating_range=game.enforce_rating_range,
            rating_min=game.rating_min,
            rating_max=game.rating_max,
        )


class MapsMetadataParserThread(QThread):
    def run(self) -> None:
        maps.CachedMapsMetadata.initial_parse()


class HostGameWidget(QDialog):
    launch = QtCore.pyqtSignal(object, object)

    # FIXME: there must be a way to make it less verbose
    def __init__(self, client: ClientWindow) -> None:
        super().__init__(client)
        self.setWindowTitle("Host Game")
        self.setObjectName("hostGameDialog")

        self.ui = HostGameDialogUi()
        self.ui.setupUi(self)

        self.client = client
        self.game = None
        self.mods: dict[str, ModInfo] = {}
        self.connect_signals()
        self.ui.mapFiltersWidget.hide()

        self.maps_metadata_parser_thread = MapsMetadataParserThread()
        self.maps_metadata_parser_thread.started.connect(self.ui.mapsLoadingLabel.show)
        self.maps_metadata_parser_thread.finished.connect(self.ui.mapsLoadingLabel.hide)
        self.maps_metadata_parser_thread.finished.connect(self.setup_maplist)

        unseen_mapgen_color = util.THEME.find_stylesheet_attribute(
            "SpecialListWidgetColors::custom",
            "background",
        )
        self._unseen_mapgen_brush = QBrush(QColor(unseen_mapgen_color))

        self._filter_timer = QTimer()
        self._filter_timer.setSingleShot(True)
        self._filter_timer.timeout.connect(self._do_apply_map_filters)

    def connect_signals(self) -> None:
        self.ui.mapList.currentRowChanged.connect(self.map_changed)
        self.ui.hostButton.released.connect(self.hosting)
        self.ui.generateButton.released.connect(self.generateMap)
        self.ui.selectRandomMapButton.clicked.connect(self.select_random_map)
        self.ui.titleEdit.textChanged.connect(self.update_text)

        self.ui.saveAndCloseButton.clicked.connect(self.save_and_quit)
        self.ui.deselectSimMods.clicked.connect(partial(self.deselect_mods, ui=False))
        self.ui.deselectUiMods.clicked.connect(partial(self.deselect_mods, ui=True))

        self.ui.passCheck.toggled.connect(self.update_pass_check)
        self.ui.enforceRatingCheck.toggled.connect(self.update_rating_enforcement)
        self.ui.radioFriends.toggled.connect(self.update_visibility)

        self.ui.mapFiltersButton.clicked.connect(self.show_hide_advanced_map_filters)
        self.ui.resetMapFiltersButton.clicked.connect(self.reset_advanced_map_filters)

        self.ui.mapWidthSlider.sliderMoved.connect(self.on_map_w_slider_moved)
        self.ui.mapHeightSlider.sliderMoved.connect(self.on_map_h_slider_moved)
        self.ui.mapPlayersSlider.sliderMoved.connect(self.on_map_p_slider_moved)

        self.ui.mapWidthMinimum.valueChanged.connect(self.on_map_min_w_changed)
        self.ui.mapWidthMaximum.valueChanged.connect(self.on_map_max_w_changed)

        self.ui.mapHeightMinimum.valueChanged.connect(self.on_map_min_h_changed)
        self.ui.mapHeightMaximum.valueChanged.connect(self.on_map_max_h_changed)

        self.ui.mapPlayersMinimum.valueChanged.connect(self.on_map_min_p_changed)
        self.ui.mapPlayersMaximum.valueChanged.connect(self.on_map_max_p_changed)

        self.ui.modTypeRadioGroup.buttonToggled.connect(self.on_mod_display_type_changed)

        self.ui.mapNameFilter.textChanged.connect(self.filter_maps_by_name)
        self.ui.modNameFilter.textChanged.connect(self.filter_mods_by_name)

        self.ui.showFavouritesOnlyCheck.toggled.connect(self.apply_map_filters)
        self.ui.toggleFavouriteButton.clicked.connect(self.toggle_favourite_map)

        self.ui.mapNameLabel.clicked.connect(self.copy_map_name_to_clipboard)
        self.ui.mapPreviewLabel.clicked.connect(self.show_large_map_preview)

    def show_large_map_preview(self) -> None:
        cur_item = self.ui.mapList.currentItem()
        if cur_item is None:
            return
        map_info = cur_item.data(QtCore.Qt.ItemDataRole.UserRole)
        if map_info["map_type"].lower().startswith("campaign"):
            return
        map_path = maps.folderForMap(map_info["folder_name"])
        if map_path is None:
            return
        pixmap = create_largest_preview(self.screen(), map_path)
        dialog = MapPreviewDialog(pixmap, self)
        dialog.exec()
        dialog.deleteLater()

    def show_hide_advanced_map_filters(self) -> None:
        self.ui.mapFiltersWidget.setVisible(not self.ui.mapFiltersWidget.isVisible())

    def reset_advanced_map_filters(self) -> None:
        self.ui.mapWidthMinimum.setValue(0)
        self.ui.mapWidthMaximum.setValue(100)
        self.ui.mapHeightMinimum.setValue(0)
        self.ui.mapHeightMaximum.setValue(100)
        self.ui.mapPlayersMinimum.setValue(0)
        self.ui.mapPlayersMaximum.setValue(16)

    def on_mod_display_type_changed(self, button: QAbstractButton, checked: bool) -> None:
        if not checked:
            return
        for i in range(self.ui.modList.count()):
            item = self.ui.modList.item(i)
            assert item is not None
            mod = self.mods[item.text()]
            if self.ui.modAllRadio.isChecked():
                item.setHidden(False)
            elif self.ui.modUiRadio.isChecked():
                item.setHidden(not mod.ui_only)
            elif self.ui.modSimRadio.isChecked():
                item.setHidden(mod.ui_only)
        Settings.set("fa.games/displayed_mods", button.text())

    def on_map_min_w_changed(self, v: int) -> None:
        v = min(v, self.ui.mapWidthMaximum.value())
        with block_signals(self.ui.mapWidthMinimum) as sb:
            sb.setValue(v)
        with block_signals(self.ui.mapWidthSlider) as slider:
            _, high = slider.get_position()
            slider.update_position(v, high)
        self.apply_map_filters()

    def on_map_max_w_changed(self, v: int) -> None:
        v = max(v, self.ui.mapWidthMinimum.value())
        with block_signals(self.ui.mapWidthMaximum) as sb:
            sb.setValue(v)
        with block_signals(self.ui.mapWidthSlider) as slider:
            low, _ = slider.get_position()
            slider.update_position(low, v)
        self.apply_map_filters()

    def on_map_min_h_changed(self, v: int) -> None:
        v = min(v, self.ui.mapHeightMaximum.value())
        with block_signals(self.ui.mapHeightMinimum) as sb:
            sb.setValue(v)
        with block_signals(self.ui.mapHeightSlider) as slider:
            _, high = slider.get_position()
            slider.update_position(v, high)
        self.apply_map_filters()

    def on_map_max_h_changed(self, v: int) -> None:
        v = max(v, self.ui.mapHeightMinimum.value())
        with block_signals(self.ui.mapHeightMaximum) as sb:
            sb.setValue(v)
        with block_signals(self.ui.mapHeightSlider) as slider:
            low, _ = slider.get_position()
            slider.update_position(low, v)
        self.apply_map_filters()

    def on_map_min_p_changed(self, v: int) -> None:
        v = min(v, self.ui.mapPlayersMaximum.value())
        with block_signals(self.ui.mapPlayersMinimum) as sb:
            sb.setValue(v)
        with block_signals(self.ui.mapPlayersSlider) as slider:
            _, high = slider.get_position()
            slider.update_position(v, high)
        self.apply_map_filters()

    def on_map_max_p_changed(self, v: int) -> None:
        v = max(v, self.ui.mapPlayersMinimum.value())
        with block_signals(self.ui.mapPlayersMaximum) as sb:
            sb.setValue(v)
        with block_signals(self.ui.mapPlayersSlider) as slider:
            low, _ = slider.get_position()
            slider.update_position(low, v)
        self.apply_map_filters()

    def filter_maps_by_name(self, text: str) -> None:
        self.apply_map_filters()
        if text == "" and (items := self.ui.mapList.selectedItems()):
            item, = items
            self.ui.mapList.scrollToItem(item)

    def apply_map_filters(self) -> None:
        if self.ui.mapList.count() >= 1500:  # why 1500? it felt like it
            self._filter_timer.start(100)
        else:
            self._do_apply_map_filters()

    def _do_apply_map_filters(self) -> None:
        w_min, w_max = self.ui.mapWidthMinimum.value(), self.ui.mapWidthMaximum.value()
        h_min, h_max = self.ui.mapHeightMinimum.value(), self.ui.mapHeightMaximum.value()
        p_min, p_max = self.ui.mapPlayersMinimum.value(), self.ui.mapPlayersMaximum.value()
        name_filter = self.ui.mapNameFilter.text().lower()
        show_favourites_only = self.ui.showFavouritesOnlyCheck.isChecked()

        for row in range(self.ui.mapList.count()):
            item = self.ui.mapList.item(row)
            if item is None:
                continue
            map_info = item.data(QtCore.Qt.ItemDataRole.UserRole)

            name_matches = name_filter in item.text().lower()
            is_favourite = map_info["folder_name"] in maps.FavouriteMaps

            size = MapSize(*map(int, map_info["map_size"].values()))
            size_matches = w_min <= size.width_km <= w_max and h_min <= size.height_km <= h_max

            players_matches = p_min <= map_info["max_players"] <= p_max

            hide = not (name_matches and size_matches and players_matches)
            if show_favourites_only:
                item.setHidden(hide or not is_favourite)
            else:
                item.setHidden(hide)

    def on_map_w_slider_moved(self, mn: int, mx: int) -> None:
        with block_signals(self.ui.mapWidthMinimum) as sb:
            sb.setValue(mn)
        with block_signals(self.ui.mapWidthMaximum) as sb:
            sb.setValue(mx)
        self.apply_map_filters()

    def on_map_h_slider_moved(self, mn: int, mx: int) -> None:
        with block_signals(self.ui.mapHeightMinimum) as sb:
            sb.setValue(mn)
        with block_signals(self.ui.mapHeightMaximum) as sb:
            sb.setValue(mx)
        self.apply_map_filters()

    def on_map_p_slider_moved(self, mn: int, mx: int) -> None:
        with block_signals(self.ui.mapPlayersMinimum) as sb:
            sb.setValue(mn)
        with block_signals(self.ui.mapPlayersMaximum) as sb:
            sb.setValue(mx)
        self.apply_map_filters()

    def filter_mods_by_name(self, text: str) -> None:
        lower_text = text.lower()
        for row in range(self.ui.modList.count()):
            item = self.ui.modList.item(row)
            if item is None:
                continue
            if lower_text == "":
                item.setHidden(False)
                continue
            mod = self.mods[item.text()]
            text_matches = lower_text in item.text().lower()
            if self.ui.modAllRadio.isChecked():
                item.setHidden(not text_matches)
            elif self.ui.modUiRadio.isChecked():
                item.setHidden(not text_matches or not mod.ui_only)
            elif self.ui.modSimRadio.isChecked():
                item.setHidden(not text_matches or mod.ui_only)

    def setup(self, title: str, game: Game) -> None:
        maps.FavouriteMaps.load_from_cache()
        UnseenMapgenNames.load_from_cache()
        self._reset()
        self.game = game

        self.password = util.settings.value("fa.games/password", "")

        self.setWindowTitle("Hosting Game : " + title)
        self.ui.titleEdit.setText(game.title)
        self.ui.passEdit.setText(self.password)
        self.ui.passCheck.setChecked(self.game.password_protected)
        self.ui.radioFriends.setChecked(self.game.visibility == GameVisibility.FRIENDS)
        self.ui.enforceRatingCheck.setChecked(self.game.enforce_rating_range)
        if self.game.rating_min is not None:
            self.ui.ratingMinSpinBox.setValue(self.game.rating_min)
        if self.game.rating_max is not None:
            self.ui.ratingMaxSpinBox.setValue(self.game.rating_max)

        self.maps_metadata_parser_thread.start()

        for mod in getInstalledMods():
            self.mods[mod.totalname] = mod
            self.ui.modList.addItem(mod.totalname)

        names = [mod.totalname for mod in getActiveMods(temporary=False)]
        logger.debug("Active Mods detected: %s", names)
        for name in names:
            ml = self.ui.modList.findItems(name, QtCore.Qt.MatchFlag.MatchExactly.MatchExactly)
            logger.debug("found item: %s", ml[0].text())
            if ml:
                ml[0].setSelected(True)

        mod_type = Settings.get("fa.games/displayed_mods", "All")
        for button in self.ui.modTypeRadioGroup.buttons():
            if mod_type == button.text():
                if button.isChecked():
                    self.on_mod_display_type_changed(button, True)
                else:
                    button.setChecked(True)
                break

    def _reset(self) -> None:
        self.ui.mapList.clear()
        self.mods.clear()
        self.ui.modList.clear()

    def setup_maplist(self) -> None:
        self.ui.mapList.clear()

        game = self.game
        current_map_item = None
        if game.featured_mod != "coop":
            allmaps = maps.CachedMapsMetadata.get_installed_maps()
            for folder_name, map_info in allmaps.items():
                if map_info["map_type"].lower().startswith("campaign"):
                    continue
                name = maps.getDisplayName(folder_name.lower())
                item = QListWidgetItem(name)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, map_info)
                self.ui.mapList.addItem(item)
                if folder_name == game.mapname:
                    current_map_item = item
                elif map_info["name"] in UnseenMapgenNames:
                    item.setForeground(self._unseen_mapgen_brush)

            self.ui.mapList.sortItems()
            self.filter_maps_by_name(self.ui.mapNameFilter.text())
            self.ui.mapsGroup.show()
            self.ui.previewGroup.show()
            if current_map_item is not None:
                self.ui.mapList.setCurrentItem(current_map_item)
            else:
                self.ui.mapList.setCurrentRow(0)
        else:
            self.ui.mapsGroup.hide()
            self.ui.previewGroup.hide()

    def set_map(self, mapname: str) -> None:
        for i in range(self.ui.mapList.count()):
            item = self.ui.mapList.item(i)
            if item is not None and item.data(QtCore.Qt.ItemDataRole.UserRole)["name"] == mapname:
                self.ui.mapList.setCurrentRow(i)
                return

    def set_maps(self, mapnames: list[str]) -> None:
        if not mapnames:
            return

        self.ui.showFavouritesOnlyCheck.setChecked(False)

        if len(mapnames) > 1:
            UnseenMapgenNames.update(set(mapnames))

        allmaps = maps.CachedMapsMetadata.get_installed_maps()
        for name in reversed(mapnames):
            item = QListWidgetItem(name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, allmaps[name])
            item.setForeground(self._unseen_mapgen_brush)
            self.ui.mapList.addItem(item)
        self.ui.mapList.sortItems()
        self.ui.mapList.setCurrentItem(item)

    def select_random_map(self) -> None:
        visible_rows = [
            row for row in range(self.ui.mapList.count())
            if not self.ui.mapList.isRowHidden(row)
            and row != self.ui.mapList.currentRow()
        ]
        if visible_rows:
            self.ui.mapList.setCurrentRow(random.choice(visible_rows))

    def update_text(self, text: str) -> None:
        self.game.update(title=text.strip())
        self.ui.hostButton.setEnabled(text.strip() != "")

    def update_pass_check(self, checked: bool) -> None:
        self.game.update(password_protected=checked)
        self.ui.passEdit.setEnabled(checked)

    def update_rating_enforcement(self, enforce: bool) -> None:
        self.game.update(enforce_rating_range=enforce)
        self.ui.ratingMinSpinBox.setEnabled(enforce)
        self.ui.ratingMaxSpinBox.setEnabled(enforce)

    def update_visibility(self, friends: bool) -> None:
        self.game.update(
            visibility=(
                GameVisibility.FRIENDS
                if friends
                else GameVisibility.PUBLIC
            ),
        )

    def map_changed(self, row: int) -> None:
        item = self.ui.mapList.item(row)
        if item is None:
            return

        map_info = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if (name := map_info["name"]) in UnseenMapgenNames:
            UnseenMapgenNames.discard(name)
            item.setForeground(QBrush())

        if map_info["folder_name"] in maps.FavouriteMaps:
            self.ui.toggleFavouriteButton.setText("★ Remove from Favourites")
        else:
            self.ui.toggleFavouriteButton.setText("☆ Add to Favourites")

        self.game.update(mapname=map_info["folder_name"], max_players=map_info["max_players"])
        self.update_map_preview(item)

    def toggle_favourite_map(self) -> None:
        item = self.ui.mapList.currentItem()
        if item is None:
            return
        map_info = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if maps.FavouriteMaps.toggle(map_info["folder_name"]):
            self.ui.toggleFavouriteButton.setText("★ Remove from Favourites")
        else:
            self.ui.toggleFavouriteButton.setText("☆ Add to Favourites")
            self.apply_map_filters()

    def hosting(self) -> None:
        if not fa.instance.available():
            return

        password = None
        if self.game.password_protected:
            password = self.ui.passEdit.text()

        if self.game.enforce_rating_range:
            self.game.update(
                rating_min=self.ui.ratingMinSpinBox.value(),
                rating_max=self.ui.ratingMaxSpinBox.value(),
            )

        self.save_last_hosted_settings()
        self.save_active_mods()

        self.launch.emit(self.game, password)
        self.done(0)

    def save_active_mods(self) -> None:
        mods = [
            self.mods[moditem.text()]
            for moditem in self.ui.modList.selectedItems()
        ]
        setActiveMods(mods, None, False)

    def save_last_hosted_settings(self) -> None:
        util.settings.beginGroup("fa.games")
        if self.game.featured_mod != "coop":
            util.settings.setValue("gamemap", self.game.mapname)
        util.settings.setValue("gamename", self.game.title)
        util.settings.setValue("friends_only", self.ui.radioFriends.isChecked())

        util.settings.setValue("password", self.ui.passEdit.text())

        util.settings.setValue("enforce_rating_range", self.ui.enforceRatingCheck.isChecked())
        util.settings.setValue("rating_min", self.ui.ratingMinSpinBox.value())
        util.settings.setValue("rating_max", self.ui.ratingMaxSpinBox.value())

        util.settings.endGroup()

    def save_and_quit(self) -> None:
        self.save_last_hosted_settings()
        self.save_active_mods()
        self.done(1)

    def deselect_mods(self, *, ui: bool) -> None:
        for i in range(self.ui.modList.count()):
            item = self.ui.modList.item(i)
            assert item is not None
            mod = self.mods[item.text()]
            if (
                    (ui and mod.ui_only)
                    or (not ui and not mod.ui_only)
            ):
                item.setSelected(False)

    @QtCore.pyqtSlot()
    def generateMap(self) -> None:
        dialog = MapGenDialog(self.client, self.client.map_generator)
        dialog.map_generated.connect(self.set_maps)
        dialog.load_cmd_options()
        dialog.exec()
        dialog.deleteLater()

    def update_map_preview(self, item: QListWidgetItem) -> None:
        map_info = cast(maps.CachedMapInfo, item.data(QtCore.Qt.ItemDataRole.UserRole))
        self.ui.mapNameLabel.setText(item.text())
        self.ui.mapNameLabel.setToolTip(map_info["name"])

        w, h = map(int, map_info["map_size"].values())
        self.ui.mapSizeLabel.setText(f"⛶  {MapSize(w, h)}")

        self.ui.mapPlayersLabel.setText(f"🧑‍🤝‍🧑 {map_info['max_players']}")

        desc_no_loc = re.sub(r"<LOC.*[D|d]escription>", "", map_info["description"])
        desc = re.sub(r"(\\r)?\\n", "\n", desc_no_loc)
        self.ui.mapDescription.setText(desc)

        version = map_info["version"]
        if version == "-":
            self.ui.mapVersionLabel.setText("")
        else:
            self.ui.mapVersionLabel.setText(f"v{version}")

        img = maps.preview(map_info["folder_name"], pixmap=True, large=True)
        if img is None:
            self.ui.mapPreviewLabel.setPixmap(QPixmap())
        elif isinstance(img, QIcon):
            self.ui.mapPreviewLabel.setPixmap(img.pixmap(256, 256))
        else:
            self.ui.mapPreviewLabel.setPixmap(img.scaled(256, 256))

    def copy_map_name_to_clipboard(self) -> None:
        map_name = self.ui.mapNameLabel.text()
        if map_name != "Copied!":
            QApplication.clipboard().setText(self.ui.mapNameLabel.toolTip())
            self.ui.mapNameLabel.setText("Copied!")
            QtCore.QTimer.singleShot(500, lambda: self.ui.mapNameLabel.setText(map_name))


def build_launcher(
        playerset: Playerset,
        me: User,
        client: ClientWindow,
) -> GameLauncher:
    widget = HostGameWidget(client)
    launcher = GameLauncher(playerset, me, client, widget)
    return launcher


class _UnseenMapgenNames:
    """Maps generated by player to host them, which were never selected"""
    def __init__(self) -> None:
        self._unseen: set[str] = set()
        self._loaded = False
        self._path = os.path.join(util.MAP_CACHE_DIR, "unseen_generated")

    def load_from_cache(self) -> None:
        if self._loaded:
            return
        try:
            with open(self._path) as f:
                self._unseen = set(f.read().splitlines())
        except FileNotFoundError:
            pass
        self._loaded = True

    def save_to_cache(self) -> None:
        with open(self._path, "w") as f:
            f.write("\n".join(self._unseen))

    def remove_cache(self) -> None:
        try:
            os.unlink(self._path)
        except FileNotFoundError:
            pass

    def cleanup(self) -> None:
        if Settings.get("maps/autodelete_generated", True, type=bool):
            self.remove_cache()
        else:
            self.save_to_cache()

    def __contains__(self, x: object) -> bool:
        return x in self._unseen

    def add(self, value: str) -> None:
        self._unseen.add(value)

    def discard(self, value: str) -> None:
        self._unseen.discard(value)

    def update(self, *s: Iterable[str]) -> None:
        self._unseen.update(*s)


UnseenMapgenNames = _UnseenMapgenNames()
