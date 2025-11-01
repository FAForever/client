import html
import os
from datetime import timedelta

import jinja2
from PyQt6 import QtCore
from PyQt6 import QtGui
from PyQt6 import QtWidgets

from src import util
from src.fa import maps
from src.fa.maps_.preview import create_largest_preview
from src.fa.maps_.previewdialog import MapPreviewDialog
from src.games.gamemodelitem import GameModelItem
from src.mapGenerator.mapgenManager import MapGeneratorManager
from src.model.game import Game
from src.qt.itemviews.styleditemdelegate import StyledItemDelegate


class GameView(QtCore.QObject):
    """
    Helps with displaying games in the game widget. Forwards
    interaction with the view.
    """
    game_double_clicked = QtCore.pyqtSignal(object)

    def __init__(self, model, view, delegate):
        QtCore.QObject.__init__(self)
        self._model = model
        self._view = view
        self._delegate = delegate

        self._view.setModel(self._model)
        self._view.setItemDelegate(self._delegate)
        self._view.doubleClicked.connect(self._game_double_clicked)
        self._view.pressed.connect(self._game_clicked)
        self._view.viewport().installEventFilter(self._delegate.tooltip_filter)
        self._mapgen_manager = MapGeneratorManager()

    # TODO make it a utility function?
    def _model_items(self):
        model = self._model
        for i in range(model.rowCount(QtCore.QModelIndex())):
            yield model.index(i, 0)

    def _game_double_clicked(self, idx):
        self.game_double_clicked.emit(idx.data().game)

    def _game_clicked(self, index: QtCore.QModelIndex) -> None:
        if QtWidgets.QApplication.mouseButtons() & QtCore.Qt.MouseButton.RightButton:
            self._game_context_menu(index)
            return

        item_rect = self._view.rectForIndex(index)
        delegate = self._view.itemDelegateForIndex(index)
        local_pos = self._view.mapFromGlobal(QtGui.QCursor.pos())
        icon_clicked = local_pos.x() - item_rect.x() < delegate.ICON_SIZE
        if icon_clicked:
            gamemodelitem = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
            self._show_map_preview(gamemodelitem.game.mapname)

    def _game_context_menu(self, index: QtCore.QModelIndex) -> None:
        gamemodelitem = index.data()
        if gamemodelitem is None or gamemodelitem.game.host == gamemodelitem._me.player.login:
            return

        mapname = gamemodelitem.game.mapname

        menu = QtWidgets.QMenu(self._view)
        menu.addAction("Join game", lambda: self.game_double_clicked.emit(gamemodelitem.game))
        menu.addSeparator()
        menu.addAction("Preview map", lambda: self._get_map_and_show_preview(mapname))
        menu.popup(QtGui.QCursor.pos())

    def _get_map_and_show_preview(self, mapname: str) -> None:
        if not maps.isMapAvailable(mapname):
            self._download_map(mapname)
        self._show_map_preview(mapname)

    def _download_map(self, mapname: str) -> None:
        if maps.isGeneratedMap(mapname):
            self._mapgen_manager.generateMap(mapname)
        else:
            maps.downloadMap(mapname)

    def _show_map_preview(self, mapname: str) -> None:
        if (mapfolder := maps.folderForMap(mapname)) is None:
            return

        pixmap = create_largest_preview(self._view.screen(), mapfolder)
        preview_dialog = MapPreviewDialog(pixmap)
        preview_dialog.exec()
        preview_dialog.deleteLater()


class GameItemDelegate(StyledItemDelegate):
    ICON_RECT = 100
    ICON_CLIP_TOP_LEFT = 3
    ICON_CLIP_BOTTOM_RIGHT = -7
    ICON_SHADOW_OFFSET = 8
    BACKGROUND_COLOR = QtGui.QColor("#202020")
    SHADOW_COLOR = QtGui.QColor("#202020")
    FRAME_THICKNESS = 1
    FRAME_COLOR = QtGui.QColor("#0f0f0f")
    TEXT_OFFSET = 10
    TEXT_RIGHT_MARGIN = 5

    TEXT_WIDTH = 250
    ICON_SIZE = 110
    PADDING = 10

    def __init__(self, formatter):
        StyledItemDelegate.__init__(self)
        self._formatter = formatter
        self.tooltip_filter = GameTooltipFilter(self._formatter)

    def paint(
            self,
            painter: QtGui.QPainter | None,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex,
    ) -> None:
        if painter is None:
            return

        painter.save()

        data = index.data()
        text = self._formatter.text(data)
        icon = self._formatter.icon(data)

        self._draw_clear_option(painter, option)
        self._draw_icon_shadow(painter, option)
        self._draw_background(painter, option)
        self._draw_icon(painter, option, icon)
        self._draw_frame(painter, option)
        self._draw_text(painter, option, text)

        painter.restore()

    def _draw_background(
            self,
            painter: QtGui.QPainter,
            option: QtWidgets.QStyleOptionViewItem,
    ) -> None:
        painter.fillRect(
            option.rect.left() + self.ICON_CLIP_TOP_LEFT,
            option.rect.top() + self.ICON_CLIP_TOP_LEFT,
            self.ICON_RECT,
            self.ICON_RECT,
            self.BACKGROUND_COLOR,
        )

    def _draw_icon_shadow(self, painter, option):
        painter.fillRect(
            option.rect.left() + self.ICON_SHADOW_OFFSET,
            option.rect.top() + self.ICON_SHADOW_OFFSET,
            self.ICON_RECT,
            self.ICON_RECT,
            self.SHADOW_COLOR,
        )

    def _draw_icon(
            self,
            painter: QtGui.QPainter,
            option: QtWidgets.QStyleOptionViewItem,
            icon: QtGui.QIcon,
    ) -> None:
        rect = QtCore.QRect(
            option.rect.left() + self.ICON_CLIP_TOP_LEFT,
            option.rect.top() + self.ICON_CLIP_TOP_LEFT,
            self.ICON_RECT,
            self.ICON_RECT,
        )
        icon.paint(painter, rect, QtCore.Qt.AlignmentFlag.AlignCenter)

    def _draw_frame(self, painter, option):
        pen = QtGui.QPen()
        pen.setWidth(self.FRAME_THICKNESS)
        pen.setBrush(self.FRAME_COLOR)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawRect(
            option.rect.left() + self.ICON_CLIP_TOP_LEFT,
            option.rect.top() + self.ICON_CLIP_TOP_LEFT,
            self.ICON_RECT,
            self.ICON_RECT,
        )

    def _draw_text(self, painter, option, text):
        left_off = self.ICON_RECT + self.TEXT_OFFSET
        top_off = 0
        right_off = self.TEXT_RIGHT_MARGIN
        bottom_off = 0
        painter.translate(
            option.rect.left() + left_off,
            option.rect.top() + top_off,
        )
        clip = QtCore.QRectF(
            0,
            0,
            option.rect.width() - left_off - right_off,
            option.rect.height() - top_off - bottom_off,
        )
        html = QtGui.QTextDocument()
        html.setHtml(text)
        html.drawContents(painter, clip)

    def sizeHint(self, option, index):
        return QtCore.QSize(
            self.ICON_SIZE + self.TEXT_WIDTH + self.PADDING,
            self.ICON_SIZE,
        )


class GameTooltipFilter(QtCore.QObject):
    def __init__(self, formatter):
        QtCore.QObject.__init__(self)
        self._formatter = formatter

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.ToolTip:
            return self._handle_tooltip(obj, event)
        else:
            return super().eventFilter(obj, event)

    def _handle_tooltip(self, widget, event):
        view = widget.parent()
        idx = view.indexAt(event.pos())
        if not idx.isValid():
            return False

        tooltip_text = self._formatter.tooltip(idx.data())
        QtWidgets.QToolTip.showText(event.globalPos(), tooltip_text, widget)
        return True


class GameItemFormatter:
    FORMATTER_FAF = str(util.THEME.readfile("games/formatters/faf.html"))
    FORMATTER_MOD = str(util.THEME.readfile("games/formatters/mod.html"))

    def __init__(self, playercolors, me):
        self._colors = playercolors
        self._me = me
        self._tooltip_formatter = GameTooltipFormatter(self._me)

    def _featured_mod(self, game):
        return game.featured_mod in ["faf", "coop"]

    def _host_color(self, game):
        hostid = game.host_player.id if game.host_player is not None else -1
        return self._colors.get_user_color(hostid)

    def _age(self, game: Game) -> timedelta:
        hosted = QtCore.QDateTime.fromString(game.hosted_at, QtCore.Qt.DateFormat.ISODate)
        delta = hosted.secsTo(QtCore.QDateTime.currentDateTime())
        return timedelta(seconds=delta)

    def text(self, data: GameModelItem) -> str:
        game = data.game
        players = game.num_players - len(game.observers)
        formatting = {
            "color": self._host_color(game),
            "mapslots": game.max_players,
            "mapdisplayname": html.escape(game.mapdisplayname),
            "title": html.escape(game.title),
            "host": html.escape(game.host),
            "players": players,
            "playerstring": "player" if players == 1 else "players",
            "simmods": "modded" if game.sim_mods else "",
            "avgrating": int(game.average_rating),
            # HACK/FIXME: we don't use separate timer to update items periodically, because
            # gameswidget has automatch frames, each of which has timer to update its 'Matching In'
            # label and label updates trigger repaint for all of the items in the gameList listview.
            # This weird coupling could be eliminated if labels' layout size constraint were fixed,
            # but it implies reworking even more of the games.ui and would require new timer.
            # It can happen when/if ladder will eventually get its own tab as suggested in
            # https://github.com/FAForever/client/issues/754#issuecomment-308861910
            # but for now we will exploit this
            "age": self._age(game),
        }
        if self._featured_mod(game):
            return self.FORMATTER_FAF.format(**formatting)
        else:
            formatting["mod"] = html.escape(game.featured_mod)
            return self.FORMATTER_MOD.format(**formatting)

    def icon(self, data):
        game = data.game
        name = game.mapname.lower()
        if game.password_protected:
            return util.THEME.icon("games/private_game.png")

        icon = maps.preview(name)
        if icon is not None:
            return icon

        return util.THEME.icon("games/unknown_map.png")

    def needed_map_preview(self, data):
        game = data.game
        name = game.mapname.lower()
        if game.password_protected or maps.preview(name) is not None:
            return None
        return name

    def _game_teams(self, game):
        teams = {
            index: [
                game.to_player(name)
                if game.is_connected(name)
                else name
                for name in team
            ]
            for index, team in game.playing_teams.items()
        }

        # Sort teams into a list
        # TODO - I believe there's a convention where team 1 is 'no team'
        teamlist = sorted([indexed_team for indexed_team in teams.items()])
        teamlist = [team for index, team in teamlist]
        return teamlist

    def _game_observers(self, game):
        return [
            game.to_player(name)
            for name in game.observers
            if game.is_connected(name)
        ]

    def tooltip(self, data):
        game = data.game
        teams = self._game_teams(game)
        observers = self._game_observers(game)
        title = game.title
        title = title.replace("<", "&lt;")
        title = title.replace(">", "&gt;")
        return self._tooltip_formatter.format(
            title, teams, observers, game.sim_mods,
        )


class GameTooltipFormatter:

    def __init__(self, me):
        self._me = me
        template_abs_path = os.path.join(
            util.COMMON_DIR, "games", "gameitem.qthtml",
        )
        with open(template_abs_path) as templatefile:
            self._template = jinja2.Template(templatefile.read())

    def format(self, title, teams, observers, mods):
        icon_path = os.path.join("chat", "countries/")
        icon_abs_path = os.path.join(util.COMMON_DIR, icon_path)
        return self._template.render(
            title=title, teams=teams,
            mods=mods.values(), observers=observers,
            me=self._me.player,
            iconpath=icon_abs_path,
        )


class GameViewBuilder:
    def __init__(self, me, player_colors):
        self._me = me
        self._player_colors = player_colors

    def __call__(self, model, view):
        game_formatter = GameItemFormatter(self._player_colors, self._me)
        game_delegate = GameItemDelegate(game_formatter)
        gameview = GameView(model, view, game_delegate)
        return gameview
