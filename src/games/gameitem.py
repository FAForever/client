import os

from PyQt5 import QtCore, QtWidgets, QtGui
from fa import maps
from downloadManager import IconCallback
import util


class GameView(QtCore.QObject):
    """
    Helps with displaying games in the game widget. Handles updates to view
    unrelated to underlying data, like downloading map previews. Forwards
    interaction with the view.
    """
    game_double_clicked = QtCore.pyqtSignal(object)

    def __init__(self, model, view, delegate, dler):
        QtCore.QObject.__init__(self)
        self._model = model
        self._view = view
        self._delegate = delegate
        self._dler = dler

        self._view.setModel(self._model)
        self._view.setItemDelegate(self._delegate)
        self._delegate.map_preview_missing.connect(self.download_map_preview)
        self._view.doubleClicked.connect(self._game_double_clicked)
        self._view.viewport().installEventFilter(self._delegate.tooltip_filter)

    def download_map_preview(self, mapname):
        cb = IconCallback(mapname, self._map_preview_downloaded)
        self._dler.downloadMapPreview(mapname, cb)

    # TODO make it a utility function?
    def _model_items(self):
        model = self._model
        for i in range(model.rowCount(QtCore.QModelIndex())):
            yield model.index(i, 0)

    def _map_preview_downloaded(self, mapname, icon):
        for idx in self._model_items():
            game = idx.data().game
            if game.mapname.lower() == mapname.lower():
                # Previews are not case-preserving
                self._view.update(idx)

    def _game_double_clicked(self, idx):
        self.game_double_clicked.emit(idx.data().game)


class GameItemDelegate(QtWidgets.QStyledItemDelegate):
    map_preview_missing = QtCore.pyqtSignal(str)

    ICON_RECT = 100
    ICON_CLIP_TOP_LEFT = 3
    ICON_CLIP_BOTTOM_RIGHT = -7
    ICON_SHADOW_OFFSET = 8
    SHADOW_COLOR = QtGui.QColor("#202020")
    FRAME_THICKNESS = 1
    FRAME_COLOR = QtGui.QColor("#303030")
    TEXT_OFFSET = 10
    TEXT_RIGHT_MARGIN = 5

    TEXT_WIDTH = 250
    ICON_SIZE = 110
    PADDING = 10

    def __init__(self, formatter):
        QtWidgets.QStyledItemDelegate.__init__(self)
        self._formatter = formatter
        self.tooltip_filter = GameTooltipFilter(self._formatter)

    def paint(self, painter, option, index):
        painter.save()

        data = index.data()
        text = self._formatter.text(data)
        icon = self._formatter.icon(data)

        self._check_map_preview(data)

        self._draw_clear_option(painter, option)
        self._draw_icon_shadow(painter, option)
        self._draw_icon(painter, option, icon)
        self._draw_frame(painter, option)
        self._draw_text(painter, option, text)

        painter.restore()

    def _check_map_preview(self, data):
        needed_preview = self._formatter.needed_map_preview(data)
        if needed_preview is not None:
            self.map_preview_missing.emit(needed_preview)

    def _draw_clear_option(self, painter, option):
        option.icon = QtGui.QIcon()
        option.text = ""
        option.widget.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem,
                                          option, painter, option.widget)

    def _draw_icon_shadow(self, painter, option):
        painter.fillRect(option.rect.left() + self.ICON_SHADOW_OFFSET,
                         option.rect.top() + self.ICON_SHADOW_OFFSET,
                         self.ICON_RECT,
                         self.ICON_RECT,
                         self.SHADOW_COLOR)

    def _draw_icon(self, painter, option, icon):
        rect = option.rect.adjusted(self.ICON_CLIP_TOP_LEFT,
                                    self.ICON_CLIP_TOP_LEFT,
                                    self.ICON_CLIP_BOTTOM_RIGHT,
                                    self.ICON_CLIP_BOTTOM_RIGHT)
        icon.paint(painter, rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

    def _draw_frame(self, painter, option):
        pen = QtGui.QPen()
        pen.setWidth(self.FRAME_THICKNESS)
        pen.setBrush(self.FRAME_COLOR)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawRect(option.rect.left() + self.ICON_CLIP_TOP_LEFT,
                         option.rect.top() + self.ICON_CLIP_TOP_LEFT,
                         self.ICON_RECT,
                         self.ICON_RECT)

    def _draw_text(self, painter, option, text):
        left_off = self.ICON_RECT + self.TEXT_OFFSET
        top_off = self.TEXT_OFFSET
        right_off = self.TEXT_RIGHT_MARGIN
        bottom_off = 0
        painter.translate(option.rect.left() + left_off,
                          option.rect.top() + top_off)
        clip = QtCore.QRectF(0,
                             0,
                             option.rect.width() - left_off - right_off,
                             option.rect.height() - top_off - bottom_off)
        html = QtGui.QTextDocument()
        html.setHtml(text)
        html.drawContents(painter, clip)

    def sizeHint(self, option, index):
        return QtCore.QSize(self.ICON_SIZE + self.TEXT_WIDTH + self.PADDING,
                            self.ICON_SIZE)


class GameTooltipFilter(QtCore.QObject):
    def __init__(self, formatter):
        QtCore.QObject.__init__(self)
        self._formatter = formatter

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.ToolTip:
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
    FORMATTER_FAF = str(util.THEME.readfile("games/formatters/faf.qthtml"))
    FORMATTER_MOD = str(util.THEME.readfile("games/formatters/mod.qthtml"))

    def __init__(self, playercolors, me):
        self._colors = playercolors
        self._me = me
        self._tooltip_formatter = GameTooltipFormatter(self._me)

    def _featured_mod(self, game):
        return game.featured_mod in ["faf", "coop"]

    def _host_color(self, game):
        hostid = game.host_player.id if game.host_player is not None else -1
        return self._colors.getUserColor(hostid)

    def text(self, data):
        game = data.game
        formatting = {
            "color": self._host_color(game),
            "mapslots": game.max_players,
            "mapdisplayname": game.mapdisplayname,
            "title": game.title,
            "host": game.host,
            "players": game.num_players,
            "playerstring": "player" if game.num_players == 1 else "players",
            "avgrating": int(game.average_rating)
        }
        if self._featured_mod(game):
            return self.FORMATTER_FAF.format(**formatting)
        else:
            formatting["mod"] = game.featured_mod
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
        teams = {index: [game.to_player(name) if game.is_connected(name)
                         else name for name in team]
                 for index, team in game.playing_teams.items()}

        # Sort teams into a list
        # TODO - I believe there's a convention where team 1 is 'no team'
        teamlist = [indexed_team for indexed_team in teams.items()]
        teamlist.sort()
        teamlist = [team for index, team in teamlist]
        return teamlist

    def _game_observers(self, game):
        return [game.to_player(name) for name in game.observers
                if game.is_connected(name)]

    def tooltip(self, data):
        game = data.game
        teams = self._game_teams(game)
        observers = self._game_observers(game)
        return self._tooltip_formatter.format(teams, observers, game.sim_mods)


class GameTooltipFormatter:
    TIP_FORMAT = str(util.THEME.readfile("games/formatters/tool.qthtml"))

    def __init__(self, me):
        self._me = me

    def _teams_tooltip(self, teams):
        versus_string = (
            "<td valign='middle' height='100%'>"
            "<font color='black' size='+5'>VS</font>"
            "</td>")

        def alignment(teams):
            for i, team in enumerate(teams):
                if i == 0:
                    yield 'left', team
                elif i == len(teams) - 1:
                    yield 'right', team
                else:
                    yield 'middle', team

        team_tables = [self._team_table(team, align)
                       for align, team in alignment(teams)]
        return versus_string.join(team_tables)

    def _team_table(self, team, align):
        team_table_start = "<td><table>"
        team_table_end = "</table></td>"
        rows = [self._player_table_row(player, align) for player in team]
        return team_table_start + "".join(rows) + team_table_end

    def _player_table_row(self, player, align):
        if isinstance(player, str):
            country = "<td></td>"
        else:
            country = "<td>{country_icon}</td>"
        pname = ("<td align='{alignment}' valign='middle' width='135'>"
                 "{player}"
                 "</td>")
        order = [pname, country] if align == 'right' else [country, pname]
        player_row = "<tr>{}{}</tr>".format(*order)

        if isinstance(player, str):
            return player_row.format(alignment=align, player=player)
        else:
            return player_row.format(
                country_icon=self._country_icon_fmt(player),
                alignment=align,
                player=self._player_fmt(player))

    def _country_icon_fmt(self, player):
        icon_path_fmt = os.path.join("chat", "countries", "{}.png")
        icon_path = icon_path_fmt.format(player.country.lower())
        icon_abs_path = os.path.join(util.COMMON_DIR, icon_path)
        return "<img src='{}'>".format(icon_abs_path)

    def _player_fmt(self, player):
        if player == self._me.player:
            pformat = "<b><i>{}</b></i>"
        else:
            pformat = "{}"
        player_string = pformat.format(player.login)
        if player.rating_deviation < 200:   # FIXME: magic number
            player_string += " ({})".format(player.rating_estimate())
        return player_string

    def _observers_tooltip(self, observers):
        if not observers:
            return ""

        observer_fmt = "{country_icon} {observer}"

        observer_strings = [observer_fmt.format(
            country_icon=self._country_icon_fmt(observer),
            observer=observer.login)
            for observer in observers]
        return "Observers: " + ", ".join(observer_strings)

    def _mods_tooltip(self, mods):
        if not mods:
            return ""
        return "<br/>With: " + "<br/>".join(mods.values())

    def format(self, teams, observers, mods):
        teamtip = self._teams_tooltip(teams)
        obstip = self._observers_tooltip(observers)
        modtip = self._mods_tooltip(mods)

        if modtip:
            modtip = "<br/>" + modtip

        return self.TIP_FORMAT.format(teams=teamtip,
                                      observers=obstip,
                                      mods=modtip)


class GameViewBuilder:
    def __init__(self, me, player_colors, preview_dler):
        self._me = me
        self._player_colors = player_colors
        self._preview_dler = preview_dler

    def __call__(self, model, view):
        game_formatter = GameItemFormatter(self._player_colors, self._me)
        game_delegate = GameItemDelegate(game_formatter)
        gameview = GameView(model, view, game_delegate,
                            self._preview_dler)
        return gameview
