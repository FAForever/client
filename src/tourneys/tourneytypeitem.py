from PyQt4 import QtGui
import util
import client

tourneyType = {}


class TourneyTypeItem(QtGui.QListWidgetItem):
    def __init__(self, message, *args, **kwargs):
        QtGui.QListWidgetItem.__init__(self, *args, **kwargs)

        self.tourney = message["name"]
        self.name = message["fullname"]
        self.mod = message["mod"]

        #Load Icon and Tooltip

        tip = message["desc"]      
        self.setToolTip(tip)
        
        if message["icon"] == None :
            icon = util.icon("games/mods/faf.png")        
            self.setIcon(icon)
        else :
            # TODO : download the icon from the remote path.
            pass

        color = client.instance.getColor("player")
        self.setTextColor(QtGui.QColor(color))
        self.setText(self.name)


    def __ge__(self, other):
        ''' Comparison operator used for item list sorting '''        
        return not self.__lt__(other)
    
    
    def __lt__(self, other):
        ''' Comparison operator used for item list sorting '''        

        # Default: Alphabetical
        return self.name.lower() < other.tourney.lower()
    



