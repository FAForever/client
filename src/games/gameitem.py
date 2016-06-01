from PyQt4 import QtCore, QtGui
import trueskill
from trueskill import Rating
from fa import maps
import util
import os
from games.moditem import mod_invisible, mods

import client
import copy

class GameItemDelegate(QtGui.QStyledItemDelegate):
    
    def __init__(self, *args, **kwargs):
        QtGui.QStyledItemDelegate.__init__(self, *args, **kwargs)
        
    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
                
        painter.save()
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        
        icon = QtGui.QIcon(option.icon)
        iconsize = icon.actualSize(option.rect.size())
        
        #clear icon and text before letting the control draw itself because we're rendering these parts ourselves
        option.icon = QtGui.QIcon()        
        option.text = ""  
        option.widget.style().drawControl(QtGui.QStyle.CE_ItemViewItem, option, painter, option.widget)
        
        #Shadow
        painter.fillRect(option.rect.left()+8-1, option.rect.top()+8-1, iconsize.width(), iconsize.height(), QtGui.QColor("#202020"))

        #Icon
        icon.paint(painter, option.rect.adjusted(5-2, -2, 0, 0), QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        
        #Frame around the icon
        pen = QtGui.QPen()
        pen.setWidth(1);
        pen.setBrush(QtGui.QColor("#303030"));  #FIXME: This needs to come from theme.
        pen.setCapStyle(QtCore.Qt.RoundCap);
        painter.setPen(pen)
        painter.drawRect(option.rect.left()+5-2, option.rect.top()+5-2, iconsize.width(), iconsize.height())

        #Description
        painter.translate(option.rect.left() + iconsize.width() + 10, option.rect.top()+10)
        clip = QtCore.QRectF(0, 0, option.rect.width()-iconsize.width() - 10 - 5, option.rect.height())
        html.drawContents(painter, clip)
  
        painter.restore()
        

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        html.setTextWidth(GameItem.TEXTWIDTH)
        return QtCore.QSize(GameItem.ICONSIZE + GameItem.TEXTWIDTH + GameItem.PADDING, GameItem.ICONSIZE)  


class GameItem(QtGui.QListWidgetItem):
    TEXTWIDTH = 230
    ICONSIZE = 110
    PADDING = 10
    
    WIDTH = ICONSIZE + TEXTWIDTH
    
    FORMATTER_FAF       = unicode(util.readfile("games/formatters/faf.qthtml"))
    FORMATTER_MOD       = unicode(util.readfile("games/formatters/mod.qthtml"))
    FORMATTER_TOOL      = unicode(util.readfile("games/formatters/tool.qthtml"))
    
    def __init__(self, uid, *args, **kwargs):
        QtGui.QListWidgetItem.__init__(self, *args, **kwargs)

        self.uid            = uid
        self.mapname        = None
        self.mapdisplayname = None
        self.client         = None
        self.title          = None
        self.host           = None
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
        if not self.client.players.isFriend(self.host):
            return

        if not self.state == "playing":
            return
                
        # User doesnt want to see this in chat   
        if not self.client.livereplays:
            return

        url = self.url()
                      
        if self.mod == "faf":
            self.client.forwardLocalBroadcast(self.host, 'is playing live in <a style="color:' + self.client.getColor("url") + '" href="' + url.toString() + '">' + self.title + '</a> (on "' + self.mapdisplayname + '")')
        else:
            self.client.forwardLocalBroadcast(self.host, 'is playing ' + self.moddisplayname + ' in <a style="color:' + self.client.getColor("url") + '" href="' + url.toString() + '">' + self.title + '</a> (on "' + self.mapdisplayname + '")')
        
    
    @QtCore.pyqtSlot()
    def announceHosting(self):
        if not self.client.players.isFriend(self.host) or self.isHidden():
            return

        if not self.state == "open":
            return

        url = self.url()

        # Join url for single sword
        client.instance.urls[self.host] = url

        # No visible message if not requested   
        if not self.client.opengames:
            return
                         
        if self.mod == "faf":
            self.client.forwardLocalBroadcast(self.host, 'is hosting <a style="color:' + self.client.getColor("url") + '" href="' + url.toString() + '">' + self.title + '</a> (on "' + self.mapdisplayname + '")')
        else:
            self.client.forwardLocalBroadcast(self.host, 'is hosting ' + self.moddisplayname + ' <a style="color:' + self.client.getColor("url") + '" href="' + url.toString() + '">' + self.title + '</a> (on "' + self.mapdisplayname + '")')

    def update(self, message, client):
        '''
        Updates this item from the message dictionary supplied
        '''
        self.client  = client

        self.title = message['title']
        self.host = message['host']

        # Maps integral team numbers (from 2, with 1 "none") to lists of names.
        teams_map = dict.copy(message['teams'])
        self.password_protected = message.get('password_protected', False)
        self.mod = message['featured_mod']
        self.modVersion = message.get('featured_mod_versions', [])
        self.mods = message.get('sim_mods', {})
        self.options = message.get('options', [])
        num_players = message.get('num_players', 0)
        self.slots = message.get('max_players', 12)
        
        oldstate = self.state
        self.state  = message['state']

        # Assemble a players & teams lists
        self.teamlist = []
        self.observerlist = []

        self.setHidden((self.state != 'open') or (self.mod in mod_invisible))        

        # Clear the status for all involved players (url may change, or players may have left, or game closed)        
        for player in self.players:
            if player.login in client.urls:
                del client.urls[player.login]

        # Just jump out if we've left the game, but tell the client that all players need their states updated
        if self.state == "closed":
            client.usersUpdated.emit(self.players)
            return

        # Used to differentiate between newly added / removed and previously present players
        oldplayers = set(map(lambda p: p.login, self.players))

        # Following the convention used by the game, a team value of 1 represents "No team". Let's
        # desugar those into "real" teams now (and convert the dict to a list)
        # Also, turn the lists of names into lists of players, and build a player name list.
        self.players = []
        teams = []
        for team_index, team in teams_map.iteritems():
            if team_index == 1:
                for ffa_player in team:
                    if ffa_player in self.client.players:
                        self.players.append(self.client.players[ffa_player])
                        teams.append([self.client.players[ffa_player]])
            else:
                real_team = []
                for name in team:
                    if name in self.client.players:
                        self.players.append(self.client.players[name])
                        real_team.append(self.client.players[name])
                teams.append(real_team)

        # Tuples for feeding into trueskill.
        rating_tuples = []
        for team in teams:
            ratings_for_team = map(lambda player: Rating(player.rating_mean, player.rating_deviation), team)
            rating_tuples.append(tuple(ratings_for_team))

        try:
            self.gamequality = 100*round(trueskill.quality(rating_tuples), 2)
        except ValueError:
            self.gamequality = 0
        self.nTeams = len(teams)

        # Map preview code
        if self.mapname != message['mapname']:
            self.mapname = message['mapname']
            self.mapdisplayname = maps.getDisplayName(self.mapname)
            refresh_icon = True
        else:
            refresh_icon = False

        #Alternate icon: If private game, use game_locked icon. Otherwise, use preview icon from map library.
        if refresh_icon:
            if self.password_protected:
                icon = util.icon("games/private_game.png")
            else:            
                icon = maps.preview(self.mapname)
                if not icon:
                    self.client.downloader.downloadMap(self.mapname, self)
                    icon = util.icon("games/unknown_map.png")
                             
            self.setIcon(icon)

        strQuality = ""
        
        if self.gamequality == 0 :
            strQuality = "? %"
        else :
            strQuality = str(self.gamequality)+" %"

        if num_players == 1:
            playerstring = "player"
        else:
            playerstring = "players"

        color = client.players.getUserColor(self.host)

        self.editTooltip(teams)

        self.setText(self.FORMATTER_FAF.format(color=color, mapslots = self.slots, mapdisplayname=self.mapdisplayname, title=self.title, host=self.host, players=num_players, playerstring=playerstring, gamequality = strQuality))

        #Spawn announcers: IF we had a gamestate change, show replay and hosting announcements 
        if (oldstate != self.state):            
            if (self.state == "playing"):
                QtCore.QTimer.singleShot(5*60000, self.announceReplay) #The delay is there because we have a 5 minutes delay in the livereplay server
            elif (self.state == "open"):
                QtCore.QTimer.singleShot(35000, self.announceHosting)   #The delay is there because we currently the host needs time to choose a map

        # Update player URLs
        for player in self.players:
            client.urls[player.login] = self.url(player.id)

        # Determine which players are affected by this game's state change            
        newplayers = set(map(lambda p: p.login, self.players))
        affectedplayers = oldplayers | newplayers
        client.usersUpdated.emit(list(affectedplayers))

    def editTooltip(self, teams):
        
        observerlist    = []
        teamlist        = []

        teams_string = ""

        i = 0
        for team in teams:
            
            if team != "-1" :
                i = i + 1
                teamtxt = "<table>"

                    
                teamDisplay    = []
                for player in team:
                    displayPlayer = ""
                    playerStr = player.login

                    if player == self.client.me:
                        playerStr = ("<b><i>%s</b></i>" % player.login)

                    dev = player.rating_deviation
                    if dev < 200 :
                        playerStr += " ("+str(player.rating_estimate())+")"

                    if i == 1 :
                        displayPlayer = ("<td align = 'left' valign='center' width = '150'>%s</td>" % playerStr)
                    elif i == self.nTeams :
                        displayPlayer = ("<td align = 'right' valign='center' width = '150'>%s</td>" % playerStr)
                    else :
                        displayPlayer = ("<td align = 'center' valign='center' width = '150'>%s</td>" % playerStr)

                    country = os.path.join(util.COMMON_DIR, "chat/countries/%s.png" % (player.country or '').lower())

                    if i == self.nTeams :
                        displayPlayer += '<td width="16"><img src = "'+country+'" width="16" height="16"></td>'
                    else :
                        displayPlayer = '<td width="16"><img src = "'+country+'" width="16" height="16"></td>' + displayPlayer

                    display = ("<tr>%s</tr>" % displayPlayer)
                    teamDisplay.append(display)
                        
                members = "".join(teamDisplay)
                
                teamlist.append("<td>" +teamtxt + members + "</table></td>")
            else :
                observerlist.append(",".join(self.teams[team]))

        teams_string += "<td valign='center' height='100%'><font valign='center' color='black' size='+5'>VS</font></td>".join(teamlist)

        observers = ""
        if len(observerlist) != 0 :
            observers = "Observers : "
            observers += ",".join(observerlist)        

        mods = ""

        if self.mods:
            mods += "<br/>With " + "<br/>".join(self.mods.values())

        self.setToolTip(self.FORMATTER_TOOL.format(teams = teams_string, observers=observers, mods = mods))

    def permutations(self, items):
        """Yields all permutations of the items."""
        if items == []:
            yield []
        else:
            for i in range(len(items)):
                for j in self.permutations(items[:i] + items[i+1:]):
                    yield [items[i]] + j

    def __ge__(self, other):
        ''' Comparison operator used for item list sorting '''        
        return not self.__lt__(other)
    
    
    def __lt__(self, other):
        ''' Comparison operator used for item list sorting '''        
        if not self.client: return True # If not initialized...
        if not other.client: return False;
        
        # Friend games are on top
        if self.client.players.isFriend(self.host) and not self.client.players.isFriend(other.host): return True
        if not self.client.players.isFriend(self.host) and self.client.players.isFriend(other.host): return False

        # Sort Games
        # 0: By Player Count
        # 1: By Game Quality
        # 2: By avg. Player Rating
        try:
            sortBy = self.listWidget().sortBy
        except AttributeError:
            sortBy = 99
        if (sortBy == 0):
            return len(self.players) > len(other.players)
        elif (sortBy == 1):
            return self.gamequality > other.gamequality
        elif (sortBy == 2):
            return self.average_rating > other.average_rating
        else:
            # Default: by UID.
            return self.uid < other.uid

    @property
    def average_rating(self):
        return sum(map(lambda p: p.rating_estimate(), self.players)) / max(len(self.players), 1)
