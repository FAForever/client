from PyQt4 import QtCore, QtGui, QtWebKit
import util


class TourneyItemDelegate(QtGui.QStyledItemDelegate):
    #colors = json.loads(util.readfile("client/colors.json"))
    
    def __init__(self, *args, **kwargs):
        QtGui.QStyledItemDelegate.__init__(self, *args, **kwargs)
        self.height = 125
        
    def paint(self, painter, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
                
        painter.save()
        
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        if self.height < html.size().height() :
            self.height = html.size().height()
        
       
        option.text = ""  
        option.widget.style().drawControl(QtGui.QStyle.CE_ItemViewItem, option, painter, option.widget)
        
        #Description
        painter.translate(option.rect.left(), option.rect.top())
        #painter.fillRect(QtCore.QRect(0, 0, option.rect.width(), option.rect.height()), QtGui.QColor(36, 61, 75, 150))
        clip = QtCore.QRectF(0, 0, option.rect.width(), option.rect.height())
        html.drawContents(painter, clip)
        
        painter.restore()

    def sizeHint(self, option, index, *args, **kwargs):
        self.initStyleOption(option, index)
        html = QtGui.QTextDocument()
        html.setHtml(option.text)
        return QtCore.QSize(int(html.size().width()), int(html.size().height()))

class QWebPageChrome(QtWebKit.QWebPage):
    def __init__(self, *args, **kwargs):
        QtWebKit.QWebPage.__init__(self, *args, **kwargs)
        
    def userAgentForUrl(self, url):
        return "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.2 (KHTML, like Gecko) Chrome/15.0.874.121 Safari/535.2"

class TourneyItem(QtGui.QListWidgetItem):
    FORMATTER_SWISS_OPEN = str(util.readfile("tournaments/formatters/open.qthtml"))

    
    def __init__(self, parent, uid, *args, **kwargs):
        QtGui.QListWidgetItem.__init__(self, *args, **kwargs)

        self.uid = int(uid)

        self.parent = parent
        
        self.type = None    
        self.client = None
        self.title  = None
        self.description = None
        self.state  = None
        self.players = []
        self.playersname = []
        
        self.viewtext = ""
        self.height = 40
        self.setHidden(True)

    def update(self, message, client):
        '''
        Updates this item from the message dictionary supplied
        '''
        self.client  = client
        old_state       = self.state
        self.state      = message.get('state', "close")
        
        ''' handling the listing of the tournament '''
        self.title      = message['name']
        self.type       = message['type']
        self.url        = message['url']
        self.description    = message.get('description', "")
        self.players        = message.get('participants', [])

        if old_state != self.state and self.state == "started" :
            widget = QtWebKit.QWebView()
            webPage = QWebPageChrome()
            widget.setPage(webPage)
            widget.setUrl(QtCore.QUrl(self.url))
            self.parent.topTabs.addTab(widget, self.title)

        self.playersname= []
        for player in self.players :
            self.playersname.append(player["name"])
            if old_state != self.state and self.state == "started" and player["name"] == self.client.login :
                channel = "#" + self.title.replace(" ", "_")
                self.client.autoJoin.emit([channel])
                QtGui.QMessageBox.information(self.client, "Tournament started !", "Your tournament has started !\nYou have automatically joined the tournament channel.")

        playerstring = "<br/>".join(self.playersname)

        self.viewtext = self.FORMATTER_SWISS_OPEN.format(title=self.title, description=self.description, numreg=str(len(self.players)), playerstring=playerstring)
        self.setText(self.viewtext)
        

    def display(self):
        return self.viewtext
 
 
    def data(self, role):
        if role == QtCore.Qt.DisplayRole:
            return self.display()  
        elif role == QtCore.Qt.UserRole :
            return self
        return super(TourneyItem, self).data(role)



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
        
        
        # Default: Alphabetical
        return self.title.lower() < other.title.lower()
    


