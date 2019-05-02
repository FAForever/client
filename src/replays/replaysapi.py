from PyQt5 import QtCore, QtNetwork
import json

from config import Settings
import logging
logger = logging.getLogger(__name__)



class ReplaysApiConnector(QtCore.QObject):
    def __init__(self, dispatch):
        QtCore.QObject.__init__(self)

        self.dispatch = dispatch
        self.api = Settings.get('api') +'/data/game'
        self.manager = QtNetwork.QNetworkAccessManager()
        self.manager.finished.connect(self.onRequestFinished)

    def requestData(self, args):
        query = QtCore.QUrlQuery()
        for key, value in args.items():
            query.addQueryItem(key, str(value))
        url = QtCore.QUrl(self.api)
        url.setQuery(query)
        request = QtNetwork.QNetworkRequest(url)
        self.manager.get(request)

    def onRequestFinished(self, reply):
        if reply.error() != QtNetwork.QNetworkReply.NoError:
            logger.error("API request error:", reply.error())
        else:
            self.handleData(reply.readAll().data().decode('utf-8'))

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
