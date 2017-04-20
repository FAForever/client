from PyQt4 import QtCore, QtGui
import trueskill
from trueskill import Rating
from fa import maps
import util
import os
from games.moditem import mod_invisible, mods

import traceback

import client

import logging
logger = logging.getLogger(__name__)


class GameItemDelegate(QtGui.QStyledItemDelegate):
    
    def __init__(self, *args, **kwargs):
        QtGui.QStyledItemDelegate.__init__(self, *args, **kwargs)
        
    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
                
        painter.save()
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        
        icon = QtGui.QIcon(option.icon)

        # clear icon and text before letting the control draw itself because we're rendering these parts ourselves
        option.icon = QtGui.QIcon()        
        option.text = ""  
        option.widget.style().drawControl(QtGui.QStyle.CE_ItemViewItem, option, painter, option.widget)
        
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
        html.setTextWidth(GameItem.TEXTWIDTH)
        return QtCore.QSize(GameItem.ICONSIZE + GameItem.TEXTWIDTH + GameItem.PADDING, GameItem.ICONSIZE)  


class GameItem(QtGui.QListWidgetItem):
    TEXTWIDTH = 250
    ICONSIZE = 110
    PADDING = 10

    FORMATTER_FAF  = str(util.readfile("games/formatters/faf.qthtml"))
    FORMATTER_MOD  = str(util.readfile("games/formatters/mod.qthtml"))
    FORMATTER_TOOL = str(util.readfile("games/formatters/tool.qthtml"))
    
    def __init__(self, uid, *args, **kwargs):
        QtGui.QListWidgetItem.__init__(self, *args, **kwargs)

        self.uid            = uid
        self.mapname        = None
        self.mapdisplayname = ""
        self.title          = None
        self.host           = ""
        self.hostid         = -1
        self.teams          = []
        self.password_protected = False
        self.mod            = None
        self.mods           = None
        self.moddisplayname = None
        self.state          = None
        self.gamequality    = 0
        self.nTeams         = 0
        self.options        = []
        self.players        = []

        self.setHidden(True)
        
    def url(self, player_id=None):
        if not player_id:
            player_id = self.host

        if self.state == "playing":
            url = QtCore.QUrl()
            url.setScheme("faflive")
            url.setHost("lobby.faforever.com")
            url.setPath(str(self.uid) + "/" + str(player_id) + ".SCFAreplay")
            url.addQueryItem("map", self.mapname)
            url.addQueryItem("mod", self.mod)
            return url
        elif self.state == "open":
            url = QtCore.QUrl()
            url.setScheme("fafgame")
            url.setHost("lobby.faforever.com")
            url.setPath(str(player_id))
            url.addQueryItem("map", self.mapname)
            url.addQueryItem("mod", self.mod)
            url.addQueryItem("uid", str(self.uid))
            return url
        return None 
        
    @QtCore.pyqtSlot()
    def announceReplay(self):
        if not client.instance.players.isFriend(self.hostid):
            return

        if not self.state == "playing":
            return
                
        # User doesnt want to see this in chat   
        if not client.instance.livereplays:
            return

        url = self.url()
        istr = client.instance.getColor("url") + '" href="' + url.toString() + '">' + self.title + '</a> (on "' + self.mapdisplayname + '")'
        if self.mod == "faf":
            client.instance.forwardLocalBroadcast(self.host, 'is playing live in <a style="color:' + istr)
        else:
            client.instance.forwardLocalBroadcast(self.host, 'is playing ' + self.mod + ' in <a style="color:' + istr)
        
    
    @QtCore.pyqtSlot()
    def announceHosting(self):
        if not client.instance.players.isFriend(self.hostid) or self.isHidden():
            return

        if not self.state == "open":
            return

        url = self.url()

        # Join url for single sword
        client.instance.urls[self.host] = url

        # No visible message if not requested   
        if not client.instance.opengames:
            return
                         
        if self.mod == "faf":
            client.instance.forwardLocalBroadcast(self.host, 'is hosting <a style="color:' + client.instance.getColor("url") + '" href="' + url.toString() + '">' + self.title + '</a> (on "' + self.mapdisplayname + '")')
        else:
            client.instance.forwardLocalBroadcast(self.host, 'is hosting ' + self.mod + ' <a style="color:' + client.instance.getColor("url") + '" href="' + url.toString() + '">' + self.title + '</a> (on "' + self.mapdisplayname + '")')

    def update(self, message, old_client=None):
        """
        Updates this item from the message dictionary supplied
        """

        if old_client:
            logger.error('gamesitem.update called with 3 args')
            logger.error(traceback.format_stack())

        self.title = message['title']  # can be renamed in Lobby (now)

        if self.host == "":  # new game
            self.host = message['host']
            self.password_protected = message.get('password_protected', False)
            self.mod = message['featured_mod']

            if 'host_id' in message:
                self.hostid = message['host_id']
            else:
                self.hostid = client.instance.players.getID(self.host)

        # Maps integral team numbers (from 2, with 1 "none") to lists of names.
        teams_map = dict.copy(message['teams'])
        self.modVersion = message.get('featured_mod_versions', [])
        self.mods = message.get('sim_mods', {})
        self.options = message.get('options', [])
        num_players = message.get('num_players', 0)
        self.slots = message.get('max_players', 12)
        
        oldstate = self.state
        self.state = message['state']

        self.setHidden((self.state != 'open') or (self.mod in mod_invisible))

        # Clear the status for all involved players (url may change, or players may have left, or game closed)        
        for player in self.players:
            if player.login in client.instance.urls:
                del client.instance.urls[player.login]

        # Just jump out if we've left the game, but tell the client that all players need their states updated
        if self.state == "closed":
            client.instance.usersUpdated.emit(self.players)
            return

        # Map preview code
        if self.mapname != message['mapname']:
            self.mapname = message['mapname']
            self.mapdisplayname = maps.getDisplayName(self.mapname)
            refresh_icon = True
        else:
            refresh_icon = False

        # Used to differentiate between newly added / removed and previously present players
        oldplayers = set([p.login for p in self.players])

        # Following the convention used by the game, a team value of 1 represents "No team". Let's
        # desugar those into "real" teams now (and convert the dict to a list)
        # Also, turn the lists of names into lists of players, and build a player name list.
        self.players = []
        teams = []
        for team_index, team in teams_map.items():
            if team_index == 1:
                for ffa_player in team:
                    if ffa_player in client.instance.players:
                        self.players.append(client.instance.players[ffa_player])
                        teams.append([client.instance.players[ffa_player]])
            else:
                real_team = []
                for name in team:
                    if name in client.instance.players:
                        self.players.append(client.instance.players[name])
                        real_team.append(client.instance.players[name])
                teams.append(real_team)

        self.nTeams = len(teams)

        # Tuples for feeding into trueskill.
        rating_tuples = []
        for team in teams:
            ratings_for_team = [Rating(player.rating_mean, player.rating_deviation) for player in team]
            rating_tuples.append(tuple(ratings_for_team))

        try:
            self.gamequality = 100*round(trueskill.quality(rating_tuples), 2)
        except ValueError:
            self.gamequality = 0

        # Alternate icon: If private game, use game_locked icon. Otherwise, use preview icon from map library.
        if refresh_icon:
            if self.password_protected:
                icon = util.icon("games/private_game.png")
            else:
                icon = maps.preview(self.mapname)
                if not icon:
                    client.instance.downloader.downloadMap(self.mapname, self)
                    icon = util.icon("games/unknown_map.png")

            self.setIcon(icon)

        if self.gamequality == 0:
            strQuality = "? %"
        else:
            strQuality = str(self.gamequality)+" %"

        if num_players == 1:
            playerstring = "player"
        else:
            playerstring = "players"

        color = client.instance.players.getUserColor(self.hostid)

        self.editTooltip(teams)

        if self.mod == "faf" or self.mod == "coop":
            self.setText(self.FORMATTER_FAF.format(color=color, mapslots=self.slots, mapdisplayname=self.mapdisplayname,
                                               title=self.title, host=self.host, players=num_players,
                                               playerstring=playerstring, gamequality=strQuality))
        else:
            self.setText(self.FORMATTER_MOD.format(color=color, mapslots=self.slots, mapdisplayname=self.mapdisplayname,
                                               title=self.title, host=self.host, players=num_players, mod=self.mod,
                                               playerstring=playerstring, gamequality=strQuality))

        # Spawn announcers: IF we had a gamestate change, show replay and hosting announcements
        if oldstate != self.state:
            if self.state == "playing":  # The delay is there because we have a 5 minutes delay in the livereplay server
                QtCore.QTimer.singleShot(5*60000, self.announceReplay)
            elif self.state == "open":  # The 3.5s delay is there because the host needs time to choose a map
                QtCore.QTimer.singleShot(35000, self.announceHosting)

        # Update player URLs
        for player in self.players:
            client.instance.urls[player.login] = self.url(player.id)

        # Determine which players are affected by this game's state change            
        newplayers = set([p.login for p in self.players])
        affectedplayers = oldplayers | newplayers
        client.instance.usersUpdated.emit(list(affectedplayers))

    def editTooltip(self, teams):
        
        observerlist = []
        teamlist     = []

        teams_string = ""

        i = 0
        for team in teams:
            
            if team != "-1":
                i += 1

                teamplayer = []
                teamplayer.append("<td><table>")
                for player in team:

                    if player == client.instance.me:
                        playerStr = "<b><i>%s</b></i>" % player.login
                    else:
                        playerStr = player.login

                    if player.rating_deviation < 200:
                        playerStr += " (%s)" % str(player.rating_estimate())

                    country = os.path.join(util.COMMON_DIR, "chat/countries/%s.png" % (player.country or '').lower())

                    if i == 1:
                        player_tr = "<tr><td><img src='%s'></td>" \
                                        "<td align='left' valign='middle' width='135'>%s</td></tr>" % (country, playerStr)
                    elif i == self.nTeams:
                        player_tr = "<tr><td align='right' valign='middle' width='135'>%s</td>" \
                                        "<td><img src='%s'></td></tr>" % (playerStr, country)
                    else:
                        player_tr = "<tr><td><img src='%s'></td>" \
                                        "<td align='center' valign='middle' width='135'>%s</td></tr>" % (country, playerStr)

                    teamplayer.append(player_tr)

                teamplayer.append("</table></td>")
                members = "".join(teamplayer)

                teamlist.append(members)
            else:
                observerlist.append(",".join(self.teams[team]))

        teams_string += "<td valign='middle' height='100%'><font color='black' size='+5'>VS</font></td>".join(teamlist)

        observers = ""
        if len(observerlist) != 0:
            observers = "Observers : "
            observers += ",".join(observerlist)

        if self.mods:
            mods = "<br />With: " + "<br />".join(list(self.mods.values()))
        else:
            mods = ""

        self.setToolTip(self.FORMATTER_TOOL.format(teams=teams_string, observers=observers, mods=mods))

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
        if client.instance.players.isFriend(self.hostid) and not client.instance.players.isFriend(other.hostid): return True
        if not client.instance.players.isFriend(self.hostid) and client.instance.players.isFriend(other.hostid): return False

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
            return self.host.lower() < other.host.lower()
        else:
            # Default: by UID.
            return self.uid < other.uid

    @property
    def average_rating(self):
        return sum([p.rating_estimate() for p in self.players]) / max(len(self.players), 1)
