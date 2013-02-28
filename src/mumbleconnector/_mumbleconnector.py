# mumbleconnector for the forged alliance lobby
# Rien Broekstra <rien@rename-it.nl> 27-02-2013
#
#
# Issues to be fixed:
#
# - Connect with mumble_link to transmit PA information in order to
#   create the correct channel
#
from PyQt4 import QtCore

import os
import sys
import win32api
import time

# Link-dll to interface with the mumble client
import mumble_link

from mumbleconnector import logger

class mumbleConnector():

    mumbleHost = "sinas.rename-it.nl"
    mumbleChannelRoot = "faforever"
    mumbleLinkActive = None

    def __init__(self, client):
        self.client = client
        self.state = "closed"
        self.uid = 0
        
        # launch Mumble
        self.launch_mumble()
        
        # Add processGameInfo as a handler for the gameInfo signal
        self.client.gameInfo.connect(self.processGameInfo)
        self.client.gameExit.connect(self.processGameExit)
        
        logger.info("MumbleConnector instantiated.")

    def launch_mumble(self):
        # Launch Mumble
        # FIXME: Add a config option to disable/enable the mumbleconnector feature, and to find the mumble executable
        url = QtCore.QUrl()
        url.setScheme("mumble")
        url.setHost(self.mumbleHost)
        url.setPath(self.mumbleChannelRoot)
        url.addQueryItem("version", "1.2.0")
            
        # Launch mumble, and connect it to the faforever server
        workingdir = os.path.join('c:', os.sep, 'Program Files (x86)', 'Mumble')
        executable = os.path.join(workingdir, 'mumble.exe')
        logger.info("Launching mumble: " + executable + " " + url.toString())
        
        # We need to call this via shellexecute, because QProcess and subprocess
        # will bail out because they cannot auto elevate the process
        win32api.ShellExecute(0, "open", executable, url.toString(), workingdir, 4) # 4 == SW_SHOWNOACTIVATE == start normal, inactive

        # Connect with mumble_link
        for i in range (1,5):
            logger.info("Trying to connect link plugin: " + str(i))
            if mumble_link.setup("faforever", "The Forged Alliance Forever Lobby Channel Placement Plugin"):
                logger.info("Mumble link established")
                self.mumbleLinkActive = 1
                return
            time.sleep(i)

        logger.info("Mumble link failed")

    # When we get noticed the user quit FA, check if we are in a voice channel. If so, move us to the (silent) lobby channel
    def processGameExit(self):
        # We use the context-information to transmit the gameuid, and the identity-information to transmid the teamnumber.
        # A plugin on the server-side will pick these state changes up, and put us into the correct channel
        if self.mumbleLinkActive:
            logger.debug("Sending state change to mumble client")
            mumble_link.set_identity("0")
                    
    def processGameInfo(self, gameInfo):
        # Check whether this gameInfo signal is about a game we are in
        for team in gameInfo["teams"]:
            for player in gameInfo['teams'][team]:
                if self.client.login == player:

                    # If we're in this game, execute the state transition
                    # corresponding to the current game state
                    self.functionMapper[gameInfo["state"]](self, gameInfo)
                    return

        # Check whether this gameInfo signal is about the last game we
        # were known to be in
        if gameInfo["uid"] == self.uid:
            self.functionMapper[gameInfo["state"]](self, gameInfo)

    def state_open(self, gameInfo):
        if gameInfo["uid"] > self.uid:
            # Player started a new lobby.
            self.state = "open"
            self.uid = gameInfo["uid"]

    def state_playing(self, gameInfo):

        # Check if the state has changed (A game is launched)
        if self.state != "playing" and self.uid == gameInfo["uid"]:
            self.state = "playing"

            logger.debug(gameInfo["teams"])

            # Team -1 is observers, team 0 is "team unset", and the rest is the team number
            # Our default team is unset. If we find ourselves in a different team, we set
            # it below
            myTeam = "0"
        
            for team in gameInfo["teams"]:
                # Ignore 1-person-teams
                if len(gameInfo['teams'][team]) < 2:
                    logger.debug("Not putting 1 person team " + team + " in a channel")
                    continue
                
                for player in gameInfo['teams'][team]:
                    if self.client.login == player:
                        myTeam = team

            if myTeam != "0":
                # We use the context-information to transmit the gameuid, and the identity-information to transmid the teamnumber.
                # A plugin on the server-side will pick these state changes up, and put us into the correct channel
                if self.mumbleLinkActive:
                    logger.debug("Sending state change to mumble client")
                    mumble_link.set_identity(str(gameInfo["uid"]) + "-" + str(team))
                else:
                    logger.debug("No mumble :(")
                
    def state_closed(self, gameInfo):
        # Check if this is a transistion from playing to clsoed
        if self.state == "playing" and self.uid == gameInfo["uid"]:
            self.state = "closed"

    # Mapper dictionary from gameInfo states to state transition functions
    functionMapper = {"open" : state_open,
                      "closed" : state_closed,
                      "playing" : state_playing,
    }
    

