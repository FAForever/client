



from PyQt5 import QtCore, QtWidgets
from fa import maps
import util
from config import Settings

class TutorialItemDelegate(QtWidgets.QStyledItemDelegate):
    
    def __init__(self, *args, **kwargs):
        QtWidgets.QStyledItemDelegate.__init__(self, *args, **kwargs)
        
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
        option.widget.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, painter, option.widget)
        
        #Shadow
        painter.fillRect(option.rect.left()+8-1, option.rect.top()+8-1, iconsize.width(), iconsize.height(), QtGui.QColor("#202020"))

        #Icon
        icon.paint(painter, option.rect.adjusted(5-2, -2, 0, 0), QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        
        #Frame around the icon
        pen = QtWidgets.QPen()
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
        html.setTextWidth(TutorialItem.TEXTWIDTH)
        return QtCore.QSize(TutorialItem.ICONSIZE + TutorialItem.TEXTWIDTH + TutorialItem.PADDING, TutorialItem.ICONSIZE)  





class TutorialItem(QtWidgets.QListWidgetItem):
    TEXTWIDTH = 230
    ICONSIZE = 110
    PADDING = 10
    
    WIDTH = ICONSIZE + TEXTWIDTH
    #DATA_PLAYERS = 32
    
    
    FORMATTER_TUTORIAL = str(util.readfile("tutorials/formatters/tutorials.qthtml"))
    
    
    def __init__(self, uid, *args, **kwargs):
        QtWidgets.QListWidgetItem.__init__(self, *args, **kwargs)

        self.mapname = None
        self.mapdisplayname = None      
        self.client = None
        self.title  = None
   
    def update(self, message, client):
        '''
        Updates this item from the message dictionary supplied
        '''

        self.client = client
        self.tutorial      = message['tutorial']
        self.description   = message['description']
        self.url           = "{}/faf/tutorials/{}".format(Settings.get('content/host'), message['url'])

        # Map preview code
        if self.mapname != message['mapname']:
            self.mapname = message['mapname']
            self.mapdisplayname = maps.getDisplayName(self.mapname)

            icon = maps.preview(self.mapname)
            if not icon:
                icon = util.icon("games/unknown_map.png")
                self.client.downloader.downloadMap(self.mapname, self)
                                        
            self.setIcon(icon)

        self.setText(self.FORMATTER_TUTORIAL.format(mapdisplayname=self.mapdisplayname, title=self.tutorial, description=self.description))


        

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
       
        # Default: Alphabetical
        return self.tutorial.lower() < other.tutorial.lower()
    


