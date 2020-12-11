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
                 command = 'modvault_meta'
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
            )
            self.dispatch.dispatch(preparedData)