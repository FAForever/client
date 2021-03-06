from .ApiBase import ApiBase
import logging
logger = logging.getLogger(__name__)

class ModApiConnector(ApiBase):
    def __init__(self, dispatch):
        ApiBase.__init__(self, '/data/mod')
        self.dispatch = dispatch

    def requestData(self):
        self.request({}, self.handleData)
    
    def requestMod(self, query={}):
        self.request(query, self.handleData)

    def handleData(self, message, meta):
        if len(meta)>0:
            data = dict(
                 command = 'vault_meta'
                ,page = meta['meta']['page']
            )
            self.dispatch.dispatch(data)
        for mod in message:
            preparedData = dict(
                 command = 'modvault_info'
                ,name = mod['displayName']
                ,uid = mod['latestVersion']['uid']
                ,link = mod['latestVersion']['downloadUrl']
                ,description = mod['latestVersion']['description']
                ,author = mod['author']
                ,version = mod['latestVersion']['version']
                ,ui = mod['latestVersion']['type'] == 'UI'
                ,thumbnail = mod['latestVersion']['thumbnailUrl']
                ,date = mod['latestVersion']['updateTime']
                ,rating = 0
                ,reviews = 0
            )
            if len(mod['reviewsSummary']) > 0:
                score = mod['reviewsSummary']['score']
                reviews = mod['reviewsSummary']['reviews']
                if reviews > 0:
                    preparedData['rating'] = float('{:1.2f}'.format(score/reviews))
                    preparedData['reviews'] = reviews
            self.dispatch.dispatch(preparedData)

class MapApiConnector(ApiBase):
    def __init__(self, dispatch):
        ApiBase.__init__(self, '/data/map')
        self.dispatch = dispatch

    def requestData(self):
        self.request({}, self.handleData)
    
    def requestMap(self, query={}):
        self.request(query, self.handleData)

    def handleData(self, message, meta):
        if len(meta)>0:
            data = dict(
                 command = 'vault_meta'
                ,page = meta['meta']['page']
            )
            self.dispatch.dispatch(data)
        for _map in message:
            preparedData = dict(
                 command = 'mapvault_info'
                ,name = _map['displayName']
                ,folderName = _map['latestVersion']['folderName']
                ,link = _map['latestVersion']['downloadUrl']
                ,description = _map['latestVersion']['description']
                ,maxPlayers = _map['latestVersion']['maxPlayers']
                ,version = _map['latestVersion']['version']
                ,ranked = _map['latestVersion']['ranked']
                ,thumbnailSmall = _map['latestVersion']['thumbnailUrlSmall']
                ,thumbnailLarge = _map['latestVersion']['thumbnailUrlLarge']
                ,date = _map['latestVersion']['updateTime']
                ,height = _map['latestVersion']['height']
                ,width = _map['latestVersion']['width']
                ,rating = 0
                ,reviews = 0
            )
            if len(_map['reviewsSummary']) > 0:
                score = _map['reviewsSummary']['score']
                reviews = _map['reviewsSummary']['reviews']
                if reviews > 0:
                    preparedData['rating'] = float('{:1.2f}'.format(score/reviews))
                    preparedData['reviews'] = reviews
            self.dispatch.dispatch(preparedData)   