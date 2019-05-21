from .ApiBase import ApiBase
import logging
logger = logging.getLogger(__name__)

class ReplaysApiConnector(ApiBase):
    def __init__(self, dispatch):
        ApiBase.__init__(self, '/data/game')
        self.dispatch = dispatch

    def requestData(self, args):
        self.request(args, self.handleData)

    def handleData(self, message):
        preparedData = dict(command = "replay_vault", 
                            action = "search_result",
                            replays = {},
                            featuredMods = {},
                            maps = {},
                            players = {},
                            playerStats = {})

        preparedData['replays'] = message

        self.dispatch.dispatch(preparedData) 
