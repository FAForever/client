from PyQt5 import QtCore, QtWidgets, QtGui
from fa import maps
import util
import os
from model.game import GameState

import client

import logging
logger = logging.getLogger(__name__)


class GameItemDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, *args, **kwargs):
        QtWidgets.QStyledItemDelegate.__init__(self, *args, **kwargs)

    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)

        painter.save()

        html = QtGui.QTextDocument()
        html.setHtml(option.text)

        icon = QtGui.QIcon(option.icon)

        # clear icon and text before letting the control draw itself because we're rendering these parts ourselves
        option.icon = QtGui.QIcon()
        option.text = ""
        option.widget.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, painter, option.widget)

        # Shadow (100x100 shifted 8 right and 8 down)
        painter.fillRect(option.rect.left()+8, option.rect.top()+8, 100, 100, QtGui.QColor("#202020"))

        # Icon  (110x110 adjusted: shifts top,left 3 and bottom,right -7 -> makes/clips it to 100x100)
        icon.paint(painter, option.rect.adjusted(3, 3, -7, -7), QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        # Frame around the icon (100x100 shifted 3 right and 3 down)
        pen = QtGui.QPen()
        pen.setWidth(1)
        pen.setBrush(QtGui.QColor("#303030"))  # FIXME: This needs to come from theme.
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawRect(option.rect.left() + 3, option.rect.top() + 3, 100, 100)

        # Description (text right of map icon(100), shifted 10 more right and 10 down)
        painter.translate(option.rect.left() + 100 + 10, option.rect.top()+10)
        clip = QtCore.QRectF(0, 0, option.rect.width() - 100 - 10 - 5, option.rect.height())
        html.drawContents(painter, clip)

        painter.restore()

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)

        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        html.setTextWidth(GameItemWidget.TEXTWIDTH)
        return QtCore.QSize(GameItemWidget.ICONSIZE + GameItemWidget.TEXTWIDTH + GameItemWidget.PADDING, GameItemWidget.ICONSIZE)


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
        if game.password_protected:
            return util.THEME.icon("games/private_game.png")

        icon = maps.preview(game.mapname)
        if icon is not None:
            return icon

        return util.THEME.icon("games/unknown_map.png")

    def needs_icon(self, data):
        game = data.game
        return (not game.password_protected
                and maps.preview(game.mapname) is None)

    def _game_teams(self, game):
        teams = {index: [game.to_player(name) for name in team
                         if game.is_connected(name)]
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
        return versus_string.join([self._team_table(team) for team in teams])

    def _team_table(self, team):
        team_table_start = "<td><table>"
        team_table_end = "</table></td>"

        def alignment(team):
            for i, player in enumerate(team):
                if i == 0:
                    yield 'left', player
                elif i == len(team) - 1:
                    yield 'right', player
                else:
                    yield 'middle', player

        rows = [self._player_table_row(player, align)
                for align, player in alignment(team)]
        return team_table_start + "".join(rows) + team_table_end

    def _player_table_row(self, player, alignment):
        player_row = (
            "<tr>"
            "<td>{country_icon}</td>"
            "<td align='{align}' valign='middle' width='135'>{player}</td>"
            "</tr>")

        return player_row.format(
            country_icon=self._country_icon_fmt(player),
            align=alignment,
            player=self._player_fmt(player))

    def _country_icon_fmt(self, player):
        country_icon = "chat/countries/{}.png".format(player.country)
        icon_path = os.path.join(util.COMMON_DIR, country_icon)
        return "<img src={}>".format(icon_path)

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


class GameItemWidget(QtWidgets.QListWidgetItem):
    TEXTWIDTH = 250
    ICONSIZE = 110
    PADDING = 10

    FORMATTER_FAF = str(util.THEME.readfile("games/formatters/faf.qthtml"))
    FORMATTER_MOD = str(util.THEME.readfile("games/formatters/mod.qthtml"))
    FORMATTER_TOOL = str(util.THEME.readfile("games/formatters/tool.qthtml"))

    def __init__(self, item, *args, **kwargs):
        QtWidgets.QListWidgetItem.__init__(self, *args, **kwargs)

        self._item = item
        self.title = ""
        self.host = ""
        self.mapName = ""
        self.maxPlayers = 0
        self.players = 0
        self.textColor = "grey"
        self.modName = ""
        self.averageRating = 0

        self.tipTeams = ""
        self.tipObservers = ""
        self.tipMods = ""
        self.privateIcon = False

    def __lt__(self, other):
        return self._item < other._item

    def __ge__(self, other):
        return self._item >= other._item

    def _officialMod(self):
        return self.modName in ["faf", "coop"]

    def updateText(self):
        if self._officialMod():
            self.setText(self.FORMATTER_FAF.format(
                color=self.textColor,
                mapslots=self.maxPlayers,
                mapdisplayname=maps.getDisplayName(self.mapName),
                title=self.title,
                host=self.host,
                players=self.players,
                playerstring="player" if self.players == 1 else "players",
                avgrating=self.averageRating))
        else:
            self.setText(self.FORMATTER_MOD.format(
                color=self.textColor,
                mapslots=self.maxPlayers,
                mapdisplayname=maps.getDisplayName(self.mapName),
                title=self.title,
                host=self.host,
                players=self.players,
                mod=self.modName,
                playerstring="player" if self.players == 1 else "players",
                avgrating=self.averageRating))

    def updateTooltip(self):
        self.setToolTip(self.FORMATTER_TOOL.format(
                teams=self.tipTeams,
                observers=self.tipObservers,
                mods=self.tipMods))

    def clearTooltip(self):
        self.setTooltip("")

    def teamsToTooltip(self, teams, observers=[]):
        teamlist = []

        for i, team in enumerate(teams, start=1):

            teamplayer = ["<td><table>"]
            for player in team:
                if player == client.instance.me.player:
                    playerStr = "<b><i>%s</b></i>" % player.login
                else:
                    playerStr = player.login

                if player.rating_deviation < 200:
                    playerStr += " (%s)" % str(player.rating_estimate())

                country = os.path.join(util.COMMON_DIR, "chat/countries/%s.png" % (player.country or '').lower())

                if i == 1:
                    player_tr = "<tr><td><img src='%s'></td>" \
                                    "<td align='left' valign='middle' width='135'>%s</td></tr>" % (country, playerStr)
                elif i == len(teams):
                    player_tr = "<tr><td align='right' valign='middle' width='135'>%s</td>" \
                                    "<td><img src='%s'></td></tr>" % (playerStr, country)
                else:
                    player_tr = "<tr><td><img src='%s'></td>" \
                                    "<td align='center' valign='middle' width='135'>%s</td></tr>" % (country, playerStr)

                teamplayer.append(player_tr)

            teamplayer.append("</table></td>")
            members = "".join(teamplayer)
            teamlist.append(members)

        teams_string = "<td valign='middle' height='100%'><font color='black' size='+5'>VS</font></td>".join(teamlist)

        observers_string = ""
        if len(observers) != 0:
            observers_string = "Observers : "
            observers_string += ", ".join(observers)

        self.tipTeams = teams_string
        self.tipObservers = observers_string

    def modsToTooltip(self, mods):
        if mods:
            self.tipMods = "<br />With: " + "<br />".join(list(mods.values()))
            if self.tipObservers:
                self.tipObservers += "<br />"
        else:
            self.tipMods = ""

    def updateIcon(self):
        if self.privateIcon:
            icon = util.THEME.icon("games/private_game.png")
        else:
            icon = maps.preview(self.mapName)
            if not icon:
                icon = util.THEME.icon("games/unknown_map.png")
        self.setIcon(icon)


class NullSorter:
    def __init__(self):
        pass

    def lt(self, item1, item2):
        return item1.game.uid < item2.game.uid

    def verifySortOrder(self, chatter):
        pass


class GameItem():
    def __init__(self, game, me, dler, sorter=None):
        self.widget = GameItemWidget(self)

        if sorter is not None:
            self.sorter = sorter
        else:
            self.sorter = NullSorter()

        self.game = game
        self.game.gameUpdated.connect(self._gameUpdate)

        self._me = me
        self._me.relationsUpdated.connect(self._relationsUpdate)

        self._dler = dler

        self.mapdisplayname = None  # Will get set at first update
        self._hide_passworded = False
        self._gameUpdate(self.game, None)

    # Stay hidden if our game is not open
    def setHidePassworded(self, param):
        self._hide_passworded = param
        self._updateHidden()

    def _updateHidden(self):
        hide = (self.game.state != GameState.OPEN
                or (self._hide_passworded and self.game.password_protected))
        self.widget.setHidden(hide)

    def _hostColor(self):
        hostid = self.game.host_player.id if self.game.host_player is not None else -1
        return client.instance.player_colors.getUserColor(hostid)

    def _gameUpdate(self, game, old):
        w = self.widget

        # Map preview code
        # Alternate icon: If private game, use game_locked icon. Otherwise,
        # use preview icon from map library.
        if old is None or game.mapname != old.mapname:
            self.mapdisplayname = maps.getDisplayName(game.mapname)
            if game.password_protected:
                icon = util.THEME.icon("games/private_game.png")
            else:
                icon = maps.preview(game.mapname)
                if not icon:
                    self._dler.downloadMap(game.mapname)
                    icon = util.THEME.icon("games/unknown_map.png")
            w.setIcon(icon)

        teams = {index: [game.to_player(name) for name in team
                         if game.is_connected(name)]
                 for index, team in game.playing_teams.items()}

        # Sort teams into a list
        teamlist = [indexed_team for indexed_team in teams.items()]
        teamlist.sort()
        teamlist = [team for index, team in teamlist]

        self.editTooltip(teamlist, game.observers)

        w.title = game.title
        w.host = game.host
        w.mapName = game.mapname
        w.maxPlayers = game.max_players
        w.players = game.num_players
        w.textColor = self._hostColor()
        w.modName = game.featured_mod
        w.privateIcon = game.password_protected
        w.averageRating = int(self.average_rating)

        w.updateIcon()
        w.updateText()

        self._updateHidden()
        self.sorter.verifySortOrder(self)

    def _relationsUpdate(self, players):
        if self.game.host_player is None:
            return
        if self.game.host_player.id not in players:
            return
        self.widget.textColor = self._hostColor()
        self.widget.updateText()
        self.sorter.verifySortOrder(self)

    def editTooltip(self, teams, observers):
        self.widget.teamsToTooltip(teams, observers)
        self.widget.modsToTooltip(self.game.sim_mods)
        self.widget.updateTooltip()

    def __ge__(self, other):
        """ Comparison operator used for item list sorting """
        return not self.__lt__(other)

    def __lt__(self, other):
        return self.sorter.lt(self, other)

    @property
    def average_rating(self):
        players = [name for team in self.game.playing_teams.values()
                   for name in team]
        players = [self.game.to_player(name) for name in players
                   if self.game.is_connected(name)]
        if not players:
            return 0
        else:
            return sum([p.rating_estimate() for p in players]) / len(players)

    def updateIcon(self):
        self.widget.updateIcon()
