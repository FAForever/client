import logging

from .ApiBase import ApiBase

logger = logging.getLogger(__name__)


class SimModFiles(ApiBase):
    def __init__(self):
        ApiBase.__init__(self, '/data/modVersion')
        self.simModUrl = ''

    def requestData(self, queryDict):
        self.request(queryDict, self.handleData)

    def getUrlFromMessage(self, message):
        self.simModUrl = message[0]['downloadUrl']

    def requestAndGetSimModUrlByUid(self, uid):
        queryDict = dict(filter='uid=={}'.format(uid))
        self.request(queryDict, self.getUrlFromMessage)
        self.waitForCompletion()
        return self.simModUrl
