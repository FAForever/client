# mumbleconnector for the forged alliance lobby
# Rien Broekstra <rien@rename-it.nl> 27-02-2013
#
# Issues to be fixed:
#


from PyQt4 import QtCore
from PyQt4 import QtGui

import os
import sys
import win32api
import time

# Link-dll to interface with the mumble client
import mumble_link

from mumbleconnector import logger

class mumbleConnector():

    mumbleHost = "faforever.com"
    mumbleChannelRoot = "Games"
    mumbleLinkActive = None
    pluginName = "faforever"
    pluginDescription = "Forged Alliance Forever Mumbleconnector"
    mumbleSetup = None
    mumbleIdentity = None

    def __init__(self, client):
        self.client = client
        self.state = "closed"
        self.uid = 0

        # Add processGameInfo as a handler for the gameInfo signal
        self.client.gameInfo.connect(self.processGameInfo)
        self.client.gameExit.connect(self.processGameExit)
        
        logger.info("MumbleConnector instantiated.")

    #
    # Launches the Mumble application
    #
    def launchMumble(self):
        url = QtCore.QUrl()
        url.setScheme("mumble")
        url.setHost(self.mumbleHost)
        url.setPath(self.mumbleChannelRoot)
        url.setUserName(self.client.login)
        url.addQueryItem("version", "1.2.0")

        logger.info("Opening " + url.toString())
        QtGui.QDesktopServices.openUrl(url)
            
    #
    # Checks and restores the link to mumble
    #
    def checkMumble(self):

        # Check if mumble was shut down (it resets our shared memory on shutdown)
        if not self.mumbleSetup:
            # Mumble link has never been set up
            logger.debug("Mumble link has never been set up")
            return self.linkMumble()

        elif mumble_link.get_version() == 0:
            # Mumble was shut down in the meantime
            logger.debug("Mumble link has been reset")
            return self.linkMumble()

        else:
            # Mumble link is active
            logger.debug("Mumble link is active")
            return 1

    def linkMumble(self):
        # Launch mumble and connect to correct server
        self.launchMumble()

        # Try to link
        for i in range (1,10):
            logger.debug("Trying to connect link plugin: " + str(i))

            if mumble_link.setup(self.pluginName, self.pluginDescription):
                logger.info("Mumble link established")
                self.mumbleSetup = 1
                return 1

            time.sleep(i)
            
        logger.info("Mumble link failed")
        return 0

    #
    # Writes our mumbleIdentity (channel identifier) into mumble's shared memory
    #
    def updateMumbleState(self):
        if self.mumbleIdentity:
            if self.checkMumble():
                logger.debug("Updating mumble state")
                mumble_link.set_identity(self.mumbleIdentity)

    def processGameExit(self):
        self.state = "closed"
        self.mumbleIdentity = "0"
        self.updateMumbleState()
            
    def processGameInfo(self, gameInfo):
        if self.playerInTeam(gameInfo):
            self.functionMapper[gameInfo["state"]](self, gameInfo)

        self.updateMumbleState()
        return

    #
    # Helper function to determine if we are in this gameInfo signal's team
    #
    def playerInTeam(self, gameInfo):
        # Check whether this gameInfo signal is about a game we are in
        for team in gameInfo["teams"]:
            for player in gameInfo['teams'][team]:
                if self.client.login == player:
                    logger.debug("We think we are in this game:")
                    logger.debug("self.client.login: " + str(self.client.login))
                    logger.debug("gameInfo['teams']: " + str(gameInfo['teams']))
                    logger.debug("self.uid: " + str(self.uid))
                    logger.debug("gameInfo['uid']: " + str(gameInfo['uid']))
                    logger.debug(str(gameInfo))
                    return 1

        return 0

    #
    # Process a state transition to state "open"
    #
    def state_open(self, gameInfo):
        if gameInfo["uid"] > self.uid:

            # Player started a new lobby.
            self.state = "open"
            self.uid = gameInfo["uid"]

            # And join to this game's lobby channel
            self.mumbleIdentity = str(gameInfo["uid"]) + "-0"

    #
    # Process a state transition to state "playing"
    #
    def state_playing(self, gameInfo):

        # Check if our game just launched
        if self.state != "playing":
            self.state = "playing"
            self.uid = gameInfo["uid"]

            logger.debug(gameInfo["teams"])

            # Team -1 is observers, team 0 is "team unset", and the rest is the team number
            # Our default team is unset. If we find ourselves in a different team, we set
            # it below
            myTeam = "0"
        
            for team in gameInfo["teams"]:
                # Ignore 1-person-teams
                if len(gameInfo['teams'][team]) < 2:
                    logger.debug("Not putting 1 person team " + team + " in a channel")
                    #continue
                
                for player in gameInfo['teams'][team]:
                    if self.client.login == player:
                        logger.debug(player + " is in team " + str(team))
                        if team != "0":
                            self.mumbleIdentity = str(gameInfo["uid"]) + "-" + str(team)
                        else:
                            self.mumbleIdentity = "0"
                            
                        logger.debug("Set mumbleIdentity: " + self.mumbleIdentity)

                
    #
    # Process a state transition to state "closed"
    #
    def state_closed(self, gameInfo):
        pass

    # Mapper dictionary from gameInfo states to state transition functions
    functionMapper = {"open" : state_open,
                      "closed" : state_closed,
                      "playing" : state_playing,
    }
    

