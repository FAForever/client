import os
import time

import util
from PyQt5 import QtCore, QtWidgets, QtGui

from config import Settings
from fa import maps
from games.moditem import mods


class ReplayItemDelegate(QtWidgets.QStyledItemDelegate):
    
    def __init__(self, *args, **kwargs):
        QtWidgets.QStyledItemDelegate.__init__(self, *args, **kwargs)
        
    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
                
        painter.save()
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        
        icon = QtGui.QIcon(option.icon)
        iconsize = icon.actualSize(option.rect.size())
        
        # clear icon and text before letting the control draw itself because we're rendering these parts ourselves
        option.icon = QtGui.QIcon()
        option.text = ""  
        option.widget.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, painter, option.widget)
        
        # Shadow
        # painter.fillRect(option.rect.left()+8-1, option.rect.top()+8-1, iconsize.width(), iconsize.height(), QtGui.QColor("#202020"))

        # Icon
        icon.paint(painter, option.rect.adjusted(5-2, -2, 0, 0), QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        
        # Frame around the icon
#        pen = QtWidgets.QPen()
#        pen.setWidth(1)
#        pen.setBrush(QtGui.QColor("#303030"))  #FIXME: This needs to come from theme.
#        pen.setCapStyle(QtCore.Qt.RoundCap)
#        painter.setPen(pen)
#        painter.drawRect(option.rect.left()+5-2, option.rect.top()+5-2, iconsize.width(), iconsize.height())

        # Description
        painter.translate(option.rect.left() + iconsize.width() + 10, option.rect.top() + 10)
        clip = QtCore.QRectF(0, 0, option.rect.width()-iconsize.width() - 10 - 5, option.rect.height())
        html.drawContents(painter, clip)
  
        painter.restore()
        

    def sizeHint(self, option, index, *args, **kwargs):
        clip = index.model().data(index, QtCore.Qt.UserRole)
        self.initStyleOption(option, index)
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        html.setTextWidth(240)
        if clip:
            return QtCore.QSize(215, clip.height)
        else:
            return QtCore.QSize(215, 35)


class ReplayItem(QtWidgets.QTreeWidgetItem):
    # list element
    FORMATTER_REPLAY                = str(util.readfile("replays/formatters/replay.qthtml"))
    # replay-info elements
    FORMATTER_REPLAY_INFORMATION    = "<h2 align='center'>Replay UID : {uid}</h2><table border='0' cellpadding='0' cellspacing='5' align='center'><tbody>{teams}</tbody></table>"
    FORMATTER_REPLAY_TEAM_SPOILED   = "<tr><td colspan='3' align='center' valign='middle'><font size='+2'>{title}</font></td></tr>{players}"
    FORMATTER_REPLAY_FFA_SPOILED    = "<tr><td colspan='3' align='center' valign='middle'><font size='+2'>Win</font></td></tr>{winner}<tr><td colspan=3 align='center' valign='middle'><font size='+2'>Lose</font></td></tr>{players}"
    FORMATTER_REPLAY_TEAM2_SPOILED = "<td><table border=0><tr><td colspan='3' align='center' valign='middle'><font size='+2'>{title}</font></td></tr>{players}</table></td>"
    FORMATTER_REPLAY_TEAM2         = "<td><table border=0>{players}</table></td>"
    FORMATTER_REPLAY_PLAYER_SCORE   = "<td align='center' valign='middle' width='20'>{player_score}</td>"
    FORMATTER_REPLAY_PLAYER_ICON    = "<td width='40'><img src='{faction_icon_uri}' width='40' height='20'></td>"
    FORMATTER_REPLAY_PLAYER_LABEL   = "<td align='{alignment}' valign='middle' width='130'>{player_name} ({player_rating})</td>"

    def __init__(self, uid, parent, *args, **kwargs):
        QtWidgets.QTreeWidgetItem.__init__(self, *args, **kwargs)

        self.uid            = uid
        self.parent         = parent
        self.height         = 70
        self.viewtext       = None
        self.viewtextPlayer = None
        self.mapname        = None
        self.mapdisplayname = None
        self.client         = None
        self.title          = None
        self.host           = None
        
        self.startDate      = None
        self.duration       = None
        self.live_delay     = False

        self.moreInfo       = False
        self.replayInfo     = False
        self.spoiled        = False
        self.url            = "{}/faf/vault/replay_vault/replay.php?id={}".format(Settings.get('content/host'), self.uid)

        self.teams          = {}
        self.access         = None
        self.mod            = None
        self.moddisplayname = None

        self.options        = []
        self.players        = []
        self.numberplayers  = 0
        self.biggestTeam    = 0
        self.winner         = None
        self.teamWin        = None

        self.setHidden(True)
        self.extraInfoWidth  = 0  # panel with more information
        self.extraInfoHeight = 0  # panel with more information
    
    def update(self, message, client):
        """ Updates this item from the message dictionary supplied """
        
        self.client = client
        
        self.name      = message["name"]
        self.mapname   = message["map"]
        if message['end'] == 4294967295:  # = FFFF FFFF (year 2106) aka still playing
            seconds = time.time()-message['start']
            if seconds > 86400:  # more than 24 hours
                self.duration = "<font color='darkgrey'>end time<br />&nbsp;missing</font>"
            elif seconds > 7200:  # more than 2 hours
                self.duration = time.strftime('%H:%M:%S', time.gmtime(seconds)) + "<br />?playing?"
            elif seconds < 300:  # less than 5 minutes
                self.duration = time.strftime('%H:%M:%S', time.gmtime(seconds)) + "<br />&nbsp;<font color='darkred'>playing</font>"
                self.live_delay = True
            else:
                self.duration = time.strftime('%H:%M:%S', time.gmtime(seconds)) + "<br />&nbsp;playing"
        else:
            self.duration = time.strftime('%H:%M:%S', time.gmtime(message["duration"]))
        self.startHour = time.strftime("%H:%M", time.localtime(message['start']))
        self.startDate = time.strftime("%Y-%m-%d", time.localtime(message['start']))
        self.mod       = message["mod"]

        # Map preview code
        self.mapdisplayname = maps.getDisplayName(self.mapname)
      
        self.icon = maps.preview(self.mapname)
        if not self.icon:
            self.client.downloader.downloadMap(self.mapname, self, True)
            self.icon = util.icon("games/unknown_map.png")        

        if self.mod in mods:
            self.moddisplayname = mods[self.mod].name 
        else:
            self.moddisplayname = self.mod

#        self.title      = message['title']
#        self.teams      = message['teams']
#        self.access     = message.get('access', 'public')
#        self.mod        = message['featured_mod']
#        self.host       = message["host"]
#        self.options    = message.get('options', [])
#        self.numplayers = message.get('num_players', 0) 
#        self.slots      = message.get('max_players',12)

        self.viewtext = self.FORMATTER_REPLAY.format(time=self.startHour, name=self.name, map=self.mapdisplayname,
                                                     duration=self.duration, mod=self.moddisplayname)

    def infoPlayers(self, players):
        """ processes information from the server about a replay into readable extra information for the user,
                also calls method to show the information """

        self.moreInfo = True
        self.numberplayers = len(players)
        mvpscore = 0
        mvp = None
        scores = {}

        for player in players:  # player highscore
            if "score" in player:
                if player["score"] > mvpscore:
                    mvp = player
                    mvpscore = player["score"]

        for player in players:  # player -> teams & playerscore -> teamscore
            if self.mod == "phantomx" or self.mod == "murderparty":  # get ffa like into one team
                team = 1
            else:
                team = int(player["team"])

            if "score" in player:
                if team in scores:
                    scores[team] = scores[team] + player["score"]
                else:
                    scores[team] = player["score"]
            if team not in self.teams:
                self.teams[team] = [player]
            else:
                self.teams[team].append(player)

        if self.numberplayers == len(self.teams):  # some kind of FFA
            self.teams ={}
            scores = {}
            team = 1
            for player in players:  # player -> team (1)
                if team not in self.teams:
                    self.teams[team] = [player]
                else:
                    self.teams[team].append(player)

        if len(self.teams) == 1 or len(self.teams) == len(players):  # it's FFA
            self.winner = mvp
        elif len(scores) > 0:  # team highscore
            mvt = 0
            for team in scores:
                if scores[team] > mvt:
                    self.teamWin = team
                    mvt = scores[team]

        self.generateInfoPlayersHtml()

    def generateInfoPlayersHtml(self):
        """  Creates the ui and extra information about a replay,
             Either teamWin or winner must be set if the replay is to be spoiled """

        teams = ""
        winnerHTML = ""

        self.spoiled = not self.parent.spoilerCheckbox.isChecked()

        i = 0
        for team in self.teams:
            if team != -1:
                i += 1

                if len(self.teams[team]) > self.biggestTeam:  # for height of Infobox
                    self.biggestTeam = len(self.teams[team])

                players = ""
                for player in self.teams[team]:
                    alignment, playerIcon, playerLabel, playerScore = self.generatePlayerHTML(i, player)

                    if self.winner is not None and player["score"] == self.winner["score"] and self.spoiled:
                        winnerHTML += "<tr>%s%s%s</tr>" % (playerScore, playerIcon, playerLabel)
                    elif alignment == "left":
                        players += "<tr>%s%s%s</tr>" % (playerScore, playerIcon, playerLabel)
                    else:  # alignment == "right"
                        players += "<tr>%s%s%s</tr>" % (playerLabel, playerIcon, playerScore)

                if self.spoiled:
                    if self.winner is not None:  # FFA in rows: Win ... Lose ....
                        teams += self.FORMATTER_REPLAY_FFA_SPOILED.format(winner=winnerHTML, players=players)
                    else:
                        if "playing" in self.duration:
                            teamTitle = "Playing"
                        elif self.teamWin == team:
                            teamTitle = "Win"
                        else:
                            teamTitle = "Lose"

                        if len(self.teams) == 2:  # pack team in <table>
                            teams += self.FORMATTER_REPLAY_TEAM2_SPOILED.format(title=teamTitle, players=players)
                        else:  # just row on
                            teams += self.FORMATTER_REPLAY_TEAM_SPOILED.format(title=teamTitle, players=players)
                else:
                    if len(self.teams) == 2:  # pack team in <table>
                        teams += self.FORMATTER_REPLAY_TEAM2.format(players=players)
                    else:  # just row on
                        teams += players

                if len(self.teams) == 2 and i == 1:  # add the 'vs'
                    teams += "<td align='center' valign='middle' height='100%'><font color='black' size='+4'>VS</font></td>"

        if len(self.teams) == 2:  # prepare the package to 'fit in' with its <td>s
            teams = "<tr>%s</tr>" % teams

        self.replayInfo = self.FORMATTER_REPLAY_INFORMATION.format(uid=self.uid, teams=teams)

        if self.isSelected():
            self.parent.replayInfos.clear()
            self.resize()
            self.parent.replayInfos.setHtml(self.replayInfo)

    def generatePlayerHTML(self, i, player):
        if i == 2 and len(self.teams) == 2:
            alignment = "right"
        else:
            alignment = "left"

        playerLabel = self.FORMATTER_REPLAY_PLAYER_LABEL.format(player_name=player["name"],
                                                                player_rating=player["rating"], alignment=alignment)

        iconUrl = os.path.join(util.COMMON_DIR, "replays/%s.png" % self.retrieveIconFaction(player, self.mod))

        playerIcon = self.FORMATTER_REPLAY_PLAYER_ICON.format(faction_icon_uri=iconUrl)

        if self.spoiled and not self.mod == "ladder1v1":
            playerScore = self.FORMATTER_REPLAY_PLAYER_SCORE.format(player_score=player["score"])
        else:  # no score for ladder
            playerScore = self.FORMATTER_REPLAY_PLAYER_SCORE.format(player_score=" ")

        return alignment, playerIcon, playerLabel, playerScore

    @staticmethod
    def retrieveIconFaction(player, mod):
        if "faction" in player:
            if player["faction"] == 1:
                faction = "UEF"
            elif player["faction"] == 2:
                faction = "Aeon"
            elif player["faction"] == 3:
                faction = "Cybran"
            elif player["faction"] == 4:
                faction = "Seraphim"
            elif player["faction"] == 5:
                if mod == "nomads":
                    faction = "Nomads"
                else:
                    faction = "Random"
            elif player["faction"] == 6:
                if mod == "nomads":
                    faction = "Random"
                else:
                    faction = "Broken"
            else:
                faction = "Broken"
        else:
            faction = "Missing"
        return faction

    def resize(self):
        if self.isSelected():
            if self.extraInfoWidth == 0 or self.extraInfoHeight == 0:
                if len(self.teams) == 1:  # ladder, FFA
                    self.extraInfoWidth = 275
                    self.extraInfoHeight = 75 + (self.numberplayers + 1) * 25  # + 1 -> second title
                elif len(self.teams) == 2:  # Team vs Team
                    self.extraInfoWidth = 500
                    self.extraInfoHeight = 75 + self.biggestTeam * 22
                else:  # FAF
                    self.extraInfoWidth = 275
                    self.extraInfoHeight = 75 + (self.numberplayers + len(self.teams)) * 25

            self.parent.replayInfos.setMinimumWidth(self.extraInfoWidth)
            self.parent.replayInfos.setMaximumWidth(600)

            self.parent.replayInfos.setMinimumHeight(self.extraInfoHeight)
            self.parent.replayInfos.setMaximumHeight(self.extraInfoHeight)

    def pressed(self, item):
        menu = QtWidgets.QMenu(self.parent)
        actionDownload = QtWidgets.QAction("Download replay", menu)
        actionDownload.triggered.connect(self.downloadReplay)
        menu.addAction(actionDownload)
        menu.popup(QtWidgets.QCursor.pos())

    def downloadReplay(self):
        QtWidgets.QDesktopServices.openUrl(QtCore.QUrl(self.url))

    def display(self, column):
        if column == 0:
            return self.viewtext
        if column == 1:
            return self.viewtext

    def data(self, column, role):
        if role == QtCore.Qt.DisplayRole:
            return self.display(column)
        elif role == QtCore.Qt.UserRole:
            return self
        return super(ReplayItem, self).data(column, role)

    def permutations(self, items):
        """  Yields all permutations of the items. """
        if items is []:
            yield []
        else:
            for i in range(len(items)):
                for j in self.permutations(items[:i] + items[i+1:]):
                    yield [items[i]] + j

    def __ge__(self, other):
        """  Comparison operator used for item list sorting """
        return not self.__lt__(other)

    def __lt__(self, other):
        """ Comparison operator used for item list sorting """
        if not self.client: return True  # If not initialized...
        if not other.client: return False
        # Default: uid
        return self.uid < other.uid
