from PyQt5 import QtCore, QtWidgets, QtGui
import trueskill
from trueskill import Rating
from fa import maps
import util
import os
from games.moditem import mods
from model.game import GameState

import traceback

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
        icon.paint(painter, option.rect.adjusted(3, 3, -7, -7), QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        
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


class GameItemWidget(QtWidgets.QListWidgetItem):
    TEXTWIDTH = 250
    ICONSIZE = 110
    PADDING = 10

    FORMATTER_FAF  = str(util.THEME.readfile("games/formatters/faf.qthtml"))
    FORMATTER_MOD  = str(util.THEME.readfile("games/formatters/mod.qthtml"))
    FORMATTER_TOOL = str(util.THEME.readfile("games/formatters/tool.qthtml"))
    
    def __init__(self, *args, **kwargs):
        QtWidgets.QListWidgetItem.__init__(self, *args, **kwargs)

        self.title = ""
        self.host = ""
        self.mapName = ""
        self.maxPlayers = 0
        self.players = 0
        self.textColor = "grey"
        self._gameQuality = "-"
        self.modName = ""

        self.tipTeams = ""
        self.tipObservers = ""
        self.tipMods = ""
        self.privateIcon = False

    @property
    def gameQuality(self):
        return self._gameQuality

    @gameQuality.setter
    def gameQuality(self, v):
        if v is None:
            self._gameQuality = "-"
        else:
            self._gameQuality = "{} %".format(v)

    def _officialMod(self):
        return self.modName in ["faf", "coop"]

    def updateText(self):
        if self._officialMod():
            self.setText(self.FORMATTER_FAF.format(
                color = self.textColor,
                mapslots = self.maxPlayers,
                mapdisplayname = maps.getDisplayName(self.mapName),
                title = self.title,
                host = self.host,
                players = self.players,
                playerstring = "player" if self.players == 1 else "players",
                gamequality = self._gameQuality))
        else:
            self.setText(self.FORMATTER_MOD.format(
                color = self.textColor,
                mapslots = self.maxPlayers,
                mapdisplayname = self.mapName,
                title = self.title,
                host = self.host,
                players=self.players,
                mod=self.modName,
                playerstring = "player" if self.players == 1 else "players",
                gamequality=self._gameQuality))

    def updateTooltip(self):
        self.setToolTip(self.FORMATTER_TOOL.format(
                teams = self.tipTeams,
                observers = self.tipObservers,
                mods = self.tipMods))
    def clearTooltip(self):
        self.setTooltip("")

    def teamsToTooltip(self, teams, observers = []):
        teamlist     = []

        teams_string = ""

        for i, team in enumerate(teams):

            teamplayer = []
            teamplayer.append("<td><table>")
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

        teams_string += "<td valign='middle' height='100%'><font color='black' size='+5'>VS</font></td>".join(teamlist)

        observers_string = ""
        if len(observers) != 0:
            observers_string = "Observers : "
            observers_string += ",".join(observers)

        self.tipTeams = teams_string
        self.tipObservers = observers_string

    def modsToTooltip(self, mods):
        if mods:
            self.tipMods = "<br />With: " + "<br />".join(list(mods.values()))
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

class GameItem():
    def __init__(self, game, *args, **kwargs):
        self.widget = GameItemWidget()

        self.game = game
        self.game.gameUpdated.connect(self._gameUpdate)

        self.oldstate = self.game.state
        self.oldplayers = []
        self.oldmapname = None

        self.mapdisplayname = None  # Will get set at first update
        self.hostid = client.instance.players.getID(self.game.host) # Shouldn't change for a game
        self.players = [] # Will get set at first update
        self._hide_passworded = False

    # For connecting to game slot
    def _gameUpdate(self, _ = None):
        self.update()

    # Stay hidden if our game is not open
    def setHidePassworded(self, param):
        self._hide_passworded = param
        self._updateHidden()

    def _updateHidden(self):
        hide = (self.game.state != GameState.OPEN
                or (self._hide_passworded and self.game.password_protected))
        self.widget.setHidden(hide)

    def url(self, player_id=None):
        g = self.game
        if not player_id:
            player_id = g.host

        if g.state == GameState.PLAYING:
            url = QtCore.QUrl()
            url.setScheme("faflive")
            url.setHost("lobby.faforever.com")
            url.setPath("/" + str(g.uid) + "/" + str(player_id) + ".SCFAreplay")
            query = QtCore.QUrlQuery()
            query.addQueryItem("map", g.mapname)
            query.addQueryItem("mod", g.featured_mod)
            url.setQuery(query)
            return url
        elif g.state == GameState.OPEN:
            url = QtCore.QUrl()
            url.setScheme("fafgame")
            url.setHost("lobby.faforever.com")
            url.setPath("/" + str(player_id))
            query = QtCore.QUrlQuery()
            query.addQueryItem("map", g.mapname)
            query.addQueryItem("mod", g.featured_mod)
            query.addQueryItem("uid", str(g.uid))
            url.setQuery(query)
            return url
        return None

    @QtCore.pyqtSlot()
    def announceReplay(self):
        if not client.instance.me.isFriend(self.hostid):
            return

        g = self.game
        if not g.state == GameState.PLAYING:
            return

        # User doesnt want to see this in chat
        if not client.instance.livereplays:
            return

        url = self.url()
        istr = client.instance.getColor("url") + '" href="' + url.toString() + '">' + g.title + '</a> (on "' + self.mapdisplayname + '")'
        if g.featured_mod == "faf":
            client.instance.forwardLocalBroadcast(g.host, 'is playing live in <a style="color:' + istr)
        else:
            client.instance.forwardLocalBroadcast(g.host, 'is playing ' + g.featured_mod + ' in <a style="color:' + istr)


    @QtCore.pyqtSlot()
    def announceHosting(self):
        if not client.instance.me.isFriend(self.hostid) or self.isHidden():
            return

        g = self.game
        if not g.state == GameState.OPEN:
            return

        url = self.url()

        # Join url for single sword
        client.instance.urls[g.host] = url

        # No visible message if not requested
        if not client.instance.opengames:
            return

        if g.featured_mod == "faf":
            client.instance.forwardLocalBroadcast(g.host, 'is hosting <a style="color:' + client.instance.getColor("url") + '" href="' + url.toString() + '">' + g.title + '</a> (on "' + self.mapdisplayname + '")')
        else:
            client.instance.forwardLocalBroadcast(g.host, 'is hosting ' + g.featured_mod + ' <a style="color:' + client.instance.getColor("url") + '" href="' + url.toString() + '">' + g.title + '</a> (on "' + self.mapdisplayname + '")')

    def update(self):
        """
        Updates this item from the message dictionary supplied
        """

        g = self.game

        oldstate = self.oldstate
        self.oldstate = g.state

        # Clear the status for all involved players (url may change, or players may have left, or game closed)
        for player in self.players:
            if player.login in client.instance.urls:
                del client.instance.urls[player.login]

        # Just jump out if we've left the game, but tell the client that all players need their states updated
        if g.state == GameState.CLOSED:
            client.instance.usersUpdated.emit([player.id for player in self.players])
            return

        # Map preview code
        if g.mapname != self.oldmapname:
            self.oldmapname = g.mapname
            self.mapdisplayname = maps.getDisplayName(g.mapname)
            refresh_icon = True
        else:
            refresh_icon = False

        # Used to differentiate between newly added / removed and previously present players
        oldplayers = set([p.id for p in self.players])

        # Following the convention used by the game, a team value of 1 represents "No team". Let's
        # desugar those into "real" teams now (and convert the dict to a list)
        # Also, turn the lists of names into lists of players, and build a player name list.
        self.players = []
        teams = []
        observers = []

        def checkappend(self, team, pid):
            if pid in client.instance.players:
                player = client.instance.players[pid]
                self.players.append(player)
                team.append(player)

        for team_index, team in g.teams.items():
            if team_index == 1:
                for ffa_player in team:
                    ffa_team = []
                    checkappend(self, ffa_team, ffa_player)
                    if ffa_team:
                        team.append(ffa_team)
            elif team_index == -1:
                for observer in team:
                    checkappend(self, observers, observer)
            else:
                real_team = []
                for name in team:
                    checkappend(self, real_team, name)
                teams.append(real_team)

        # Tuples for feeding into trueskill.
        rating_tuples = []
        for team in teams:
            ratings_for_team = [Rating(player.rating_mean, player.rating_deviation) for player in team]
            rating_tuples.append(tuple(ratings_for_team))

        try:
            gamequality = 100*round(trueskill.quality(rating_tuples), 2)
        except ValueError:
            gamequality = None

        # Alternate icon: If private game, use game_locked icon. Otherwise, use preview icon from map library.
        if refresh_icon:
            if g.password_protected:
                icon = util.THEME.icon("games/private_game.png")
            else:
                icon = maps.preview(g.mapname)
                if not icon:
                    client.instance.downloader.downloadMap(g.mapname, self.widget)
                    icon = util.THEME.icon("games/unknown_map.png")

            self.widget.setIcon(icon)

        w = self.widget


        color = client.instance.players.getUserColor(self.hostid)

        self.editTooltip(teams)

        w.title = g.title
        w.host = g.host
        w.mapName = g.mapname
        w.maxPlayers = g.max_players
        w.players = g.num_players
        w.textColor = color
        w.gameQuality = gamequality
        w.modName = g.featured_mod
        w.privateIcon = g.password_protected

        w.updateIcon()
        w.updateText()

        # Spawn announcers: IF we had a gamestate change, show replay and hosting announcements
        if oldstate != g.state:
            if g.state == GameState.PLAYING:  # The delay is there because we have a 5 minutes delay in the livereplay server
                QtCore.QTimer.singleShot(5*60000, self.announceReplay)
            elif g.state == GameState.OPEN:  # The 3.5s delay is there because the host needs time to choose a map
                QtCore.QTimer.singleShot(35000, self.announceHosting)

        # Update player URLs
        for player in self.players:
            client.instance.urls[player.login] = self.url(player.id)

        # Determine which players are affected by this game's state change
        newplayers = set([p.id for p in self.players])
        affectedplayers = oldplayers | newplayers
        client.instance.usersUpdated.emit(list(affectedplayers))

        self._updateHidden()

    def editTooltip(self, teams):
        self.widget.teamsToTooltip(teams)
        self.widget.modsToTooltip(self.game.sim_mods)
        self.widget.updateTooltip()

    def permutations(self, items):
        """ Yields all permutations of the items. """
        if items == []:
            yield []
        else:
            for i in range(len(items)):
                for j in self.permutations(items[:i] + items[i+1:]):
                    yield [items[i]] + j

    def __ge__(self, other):
        """ Comparison operator used for item list sorting """
        return not self.__lt__(other)

    def __lt__(self, other):
        """ Comparison operator used for item list sorting """
        if not client.instance: return True  # If not initialized...

        # Friend games are on top
        if client.instance.me.isFriend(self.hostid) and not client.instance.me.isFriend(other.hostid): return True
        if not client.instance.me.isFriend(self.hostid) and client.instance.me.isFriend(other.hostid): return False

        # Sort Games
        # 0: By Player Count
        # 1: By avg. Player Rating
        # 2: By Map
        # 3: By Host
        # 4+: By age = uid
        try:
            sortby = self.listWidget().sortBy
        except AttributeError:
            sortby = 99
        if sortby == 0:
            return len(self.players) > len(other.players)
        elif sortby == 1:
            return self.average_rating > other.average_rating
        elif sortby == 2:
            return self.mapdisplayname.lower() < other.mapdisplayname.lower()
        elif sortby == 3:
            return self.game.host.lower() < other.game.host.lower()
        else:
            # Default: by UID.
            return self.game.uid < other.game.uid

    @property
    def average_rating(self):
        return sum([p.rating_estimate() for p in self.players]) / max(len(self.players), 1)
