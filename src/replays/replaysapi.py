from PyQt5 import QtCore, QtNetwork
import json
import time
import requests

from config import Settings
import logging
logger = logging.getLogger(__name__)


class ReplaysApiConnector(QtCore.QObject):
    def __init__(self, dispatch):
        QtCore.QObject.__init__(self)

        self.dispatch = dispatch
        self.api = Settings.get('api') +'/data/game'

    def requestData(self, args):
        try:
            response = requests.get(self.api, args)
        except ValueError as e:
            logger.error("API request failed")    
            logger.error(e)
            return

        if(response.ok):
            self.handleData(response.content)
        else:
            logger.debug("API error: " + str(response.status_code))
        
    
    def handleData(self, data_string):
        preparedData = dict(command = "replay_vault", 
                            action = "search_result",
                            replays = {},
                            featuredMods = {},
                            maps = {},
                            players = {},
                            playerStats = {})
                        
        try:
            message = json.loads(data_string)
        except ValueError as e:
            logger.error("Error decoding json")
            logger.error(e)
            return
        
        preparedData['replays'] = message['data']
        
        if 'included' in message:
            for includedData in message['included']:
                if includedData['type'] == "featuredMod":
                    preparedData['featuredMods'][includedData['id']] = includedData['attributes']
                elif includedData['type'] == "mapVersion":
                    preparedData['maps'][includedData['id']] = includedData['attributes']   
                elif includedData['type'] == "gamePlayerStats":
                    preparedData['playerStats'][includedData['id']] = includedData['attributes']
                    preparedData['playerStats'][includedData['id']]['playerID'] = includedData["relationships"]["player"]["data"]["id"]
                elif includedData['type'] == "player":
                    preparedData['players'][includedData['id']] = includedData['attributes']
        else:
            preparedData["No_replays"] = True

        self.dispatch.dispatch(preparedData) 
