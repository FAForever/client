import logging

from .ApiBase import ApiBase

logger = logging.getLogger(__name__)


class FeaturedModFiles(ApiBase):

    def __init__(self, mod_id, version):
        ApiBase.__init__(
            self,
            '/featuredMods/{}/files/{}'.format(mod_id, version),
        )
        self.featuredModFiles = []

    def requestData(self):
        self.request({}, self.handleData)

    def handleData(self, message):
        self.featuredModFiles = message

    def getFiles(self):
        self.requestData()
        self.waitForCompletion()
        return self.featuredModFiles


class FeaturedModId(ApiBase):
    def __init__(self):
        ApiBase.__init__(self, '/data/featuredMod')
        self.featuredModId = 0

    def requestData(self, queryDict={}):
        self.request(queryDict, self.handleData)

    def handleFeaturedModId(self, message):
        self.featuredModId = message[0]['id']

    def requestFeaturedModIdByName(self, technicalName):
        queryDict = dict(filter='technicalName=={}'.format(technicalName))
        self.request(queryDict, self.handleFeaturedModId)

    def requestAndGetFeaturedModIdByName(self, technicalName):
        self.requestFeaturedModIdByName(technicalName)
        self.waitForCompletion()
        return self.featuredModId
