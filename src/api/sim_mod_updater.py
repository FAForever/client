from .UpdaterBase import UpdaterBase
import logging
logger = logging.getLogger(__name__)

class SimModFiles(UpdaterBase):
    def __init__(self):
        UpdaterBase.__init__(self, '/data/modVersion')

    def requestData(self, queryDict):
        return self.request(queryDict, self.handleData)

    def handleData(self, message):
        return message[0]['downloadUrl']