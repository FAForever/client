



from PyQt4 import QtCore, QtGui
from fa import maps
import util
import os, time
from games.moditem import mods

import client


class ReplayItemDelegate(QtGui.QStyledItemDelegate):
    
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
        #painter.fillRect(option.rect.left()+8-1, option.rect.top()+8-1, iconsize.width(), iconsize.height(), QtGui.QColor("#202020"))

        #Icon
        icon.paint(painter, option.rect.adjusted(5-2, -2, 0, 0), QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        
        #Frame around the icon
#        pen = QtGui.QPen()
#        pen.setWidth(1);
#        pen.setBrush(QtGui.QColor("#303030"));  #FIXME: This needs to come from theme.
#        pen.setCapStyle(QtCore.Qt.RoundCap);
#        painter.setPen(pen)
#        painter.drawRect(option.rect.left()+5-2, option.rect.top()+5-2, iconsize.width(), iconsize.height())

        #Description
        painter.translate(option.rect.left() + iconsize.width() + 10, option.rect.top()+10)
        clip = QtCore.QRectF(0, 0, option.rect.width()-iconsize.width() - 10 - 5, option.rect.height())
        html.drawContents(painter, clip)
  
        painter.restore()
        

    def sizeHint(self, option, index, *args, **kwargs):
        clip = index.model().data(index, QtCore.Qt.UserRole)
        self.initStyleOption(option, index)
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        html.setTextWidth(240)
        if clip :
            return QtCore.QSize(215, clip.height)
        else :
            return QtCore.QSize(215, 35)




class ReplayItem(QtGui.QTreeWidgetItem):

    
    FORMATTER_REPLAY        = unicode(util.readfile("replays/formatters/replay.qthtml"))

    
    def __init__(self, uid, parent, *args, **kwargs):
        QtGui.QTreeWidgetItem.__init__(self, *args, **kwargs)

        
        self.uid            = uid
        self.parent         = parent
        self.height         = 70
        self.viewtext       = None
        self.viewtextPlayer = None
        self.mapname        = None
        self.mapdisplayname = None
        self.client         = None
        self.title          = None
        
        self.startDate      = None
        self.duration       = None
        
        self.moreInfo       = False
        self.replayInfo     = False
        self.spoiled        = False
        self.url            = "http://content.faforever.com/faf/vault/replay_vault/replay.php?id=%i" % self.uid
        
        self.teams          = {}
        self.access         = None
        self.mod            = None
        self.moddisplayname = None

        self.options        = []
        self.players        = []
        
        self.setHidden(True)

    
    def update(self, message, client):
        '''
        Updates this item from the message dictionary supplied
        '''
        
        
        self.client  = client
        
        self.name       = message["name"]
        self.mapname    = message["map"]
        self.duration   = time.strftime('%H:%M:%S', time.gmtime(message["duration"]))
        self.startHour  = time.strftime("%H:%M", time.localtime(message['start']))
        self.startDate  = time.strftime("%Y-%m-%d", time.localtime(message['start']))
        self.mod        = message["mod"]
         
        # Map preview code
        self.mapdisplayname = maps.getDisplayName(self.mapname)
      
        self.icon = maps.preview(self.mapname)
        if not self.icon:
            self.client.downloader.downloadMap(self.mapname, self, True)
            self.icon = util.icon("games/unknown_map.png")        
        #self.setIcon(0, self.icon)
        
        self.moddisplayname = self.mod
        self.modoptions = []

        if self.mod in mods :
            self.moddisplayname = mods[self.mod].name 

#        self.title      = message['title']
#        self.host       = message['host']
#        self.teams      = message['teams']
#        self.access     = message.get('access', 'public')
#        self.mod        = message['featured_mod']
#        self.options    = message.get('options', [])
#        self.numplayers = message.get('num_players', 0) 
#        self.slots      = message.get('max_players',12)

        self.viewtext = (self.FORMATTER_REPLAY.format(time=self.startHour, name=self.name, map = self.mapdisplayname, duration = self.duration, mod = self.moddisplayname))

    def infoPlayers(self, players):
        
        self.moreInfo = True
        scores = {}
        
        for player in players :
            team            = int(player["team"])
            

            if team :
                if "score" in player :
                    if team in scores :
                        scores[team] = scores[team] + player["score"]
                    else :
                        scores[team] = player["score"]
                if not team in self.teams :
                    self.teams[team] = [player]
                else :
                    self.teams[team].append(player)

        self.teamWin = None
        if len(scores) > 0 :
            winner = 0
            for team in scores :
                if scores[team] > winner :
                    self.teamWin = team

        self.generateInfoPlayersHtml()
                
    def generateInfoPlayersHtml(self):
        observerlist    = []
        teamlist        = []

        teams = ""
        self.spoiled = self.parent.spoilerCheckbox.isChecked() == False

        i = 0
        for team in self.teams:
            if team != -1 :
                i = i + 1
                teamtxt = "<table border=0 width = 100% height = 100%>"

                teamDisplay    = []
                if self.teamWin and self.spoiled:
                    if self.teamWin == i :
                        teamDisplay.append("<table border=0 width = 100% height = 100%><tr><td align = 'center' valign='center' width =100%><font size ='+2'>WIN</font></td></tr></table>")
                    else :
                        teamDisplay.append("<table border=0 width = 100% height = 100%><tr><td align = 'center' valign='center' width =100%><font size ='+2'>LOSE</font></td></tr></table>")
                for player in self.teams[team] :
                    displayPlayer = ""


                    playerStr = player["name"]

                    if "rating" in player :
                        playerStr += " ("+str(int(player["rating"]))+")"

                    if "after_rating" in player and self.spoiled:
                        playerStr += " to ("+str(int(player["after_rating"]))+")"


                    if i == 1 and i != len(self.teams) :
                        displayPlayer = ("<td align = 'left' valign='center' width=150>%s</td>" % playerStr)
                    elif i == len(self.teams) :
                        displayPlayer = ("<td align = 'right' valign='center' width=150>%s</td>" % playerStr)
                    else :
                        displayPlayer = ("<td align = 'center' valign='center' width=150>%s</td>" % playerStr)
                    

                    if "faction" in player :
                        if player["faction"] == 1 :
                            faction = "UEF"
                        elif player["faction"] == 2 :
                            faction = "Aeon"
                        elif player["faction"] == 3 :
                            faction = "Cybran"
                        elif player["faction"] == 4 :
                            faction = "Seraphim"                            
                        elif player["faction"] == 5 :
                            faction = "Nomads"     
                        else :
                            faction = "Broken"
                            
                        url = os.path.join(util.COMMON_DIR, "replays/%s.png" % faction)
 
                        if i == len(self.teams) : 
                            displayPlayer += '<td width="40"><img src = "'+url+'" width="40" height="20"></td>'
                        else :
                            displayPlayer = '<td width="40"><img src = "'+url+'" width="40" height="20"></td>' + displayPlayer

                    display = ("<tr>%s</tr>" % displayPlayer)

                    teamDisplay.append(display)
                        
                members = "".join(teamDisplay)
                
                teamlist.append("<td>" + teamtxt + members + "</table></td>")
                
                    
                
            else :
                observerlist.append(",".join(self.teams[team]))

        teams += "<td valign='center' height='100%'><font valign='center' color='black' size='+5'>VS</font></td>".join(teamlist)


        observers = ""
        if len(observerlist) != 0 :
            observers = "Observers : "
            observers += ",".join(observerlist)    

        #self.setToolTip(teams)
        self.replayInfo = ('<h2>Replay UID : %i</h2></br></br><table border="0" cellpadding="0" cellspacing="5"><tbody><tr>%s</tr></tbody></table>') % (self.uid, teams)
        
        
        if self.isSelected() :
            self.parent.replayInfos.clear()
            self.parent.replayInfos.setHtml(self.replayInfo)


    def pressed(self, item):
        menu = QtGui.QMenu(self.parent)
        actionDownload = QtGui.QAction("Download replay", menu)
        actionDownload.triggered.connect(self.downloadReplay)
        menu.addAction(actionDownload)
        menu.popup(QtGui.QCursor.pos())
        
    def downloadReplay(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(self.url))

    def display(self, column):
        if column == 0 :
            return self.viewtext
        if column == 1 :
            return self.viewtext   
 
    def data(self, column, role):
        if role == QtCore.Qt.DisplayRole:
            return self.display(column)  
        elif role == QtCore.Qt.UserRole :
            return self
        return super(ReplayItem, self).data(column, role)
 
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
        # Default: uid
        return self.uid < other.uid
    


