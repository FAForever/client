from PyQt4 import QtGui, QtCore
import util
from galacticWar import logger

FormClass, BaseClass = util.loadUiType("galacticwar/infopanel.ui")

class InfoPanelWidget(FormClass, BaseClass):
    def __init__(self, parent, *args, **kwargs):
        logger.debug("GW Info panel instantiating.")
        BaseClass.__init__(self, *args, **kwargs)
        
        self.setupUi(self)
        self.parent = parent
        self.galaxy = self.parent.galaxy
        
        self.setup()
        self.attackListWidget.hide()
        
        self.planet = None
        
        # Updating stats
        self.parent.creditsUpdated.connect(self.updateCredit)
        self.parent.rankUpdated.connect(self.updateRank)
        self.parent.victoriesUpdated.connect(self.updateVictories)
        
        self.parent.planetClicked.connect(self.planetClicked)
        self.parent.hovering.connect(self.setup)
        self.parent.attacksUpdated.connect(self.updateAttacks)
        
        self.attackButton.clicked.connect(self.attack)
                
    def setup(self):
        self.attackButton.hide()
        
        
    def updateAttacks(self):
        
        if self.parent.uid in self.parent.attacks :
            self.attackListWidget.show()
            self.attackListWidget.clear()
            for uid in self.parent.attacks[self.parent.uid] :
                self.attackListWidget.addItem(self.parent.galaxy.get_name(uid))
        else :
            self.attackListWidget.hide()
        
    
    def attack(self):
        self.parent.send(dict(command="attack_command", uid=self.planet))
    
    def updateRank(self, rank):
        rankName = self.parent.get_rank(self.parent.faction, rank)
        self.nameLabel.setText("%s %s" %(rankName,self.parent.name))
    
    def updateVictories(self, victories):
        self.victoriesLabel.setText("%i" % victories)
    
    def updateCredit(self, credits):
        self.creditsLabel.setText("%i / %i" % (credits, (1000+ 1000*self.parent.rank)))
    
    def planetClicked(self, planetId):
        ''' When the user click a planet on the map'''

        self.attackButton.hide()

        faction = self.parent.faction
        if faction == None :
            self.planet = None
            return
        
        if self.galaxy.control_points[planetId].occupation(faction) > 0.9 :
            self.planet = None
            return
        
        for site in self.galaxy.getLinkedPlanets(planetId) :
            if self.galaxy.control_points[site].occupation(faction) > 0.5 :
                self.attackButton.show()
                self.planet = planetId
                return

    
