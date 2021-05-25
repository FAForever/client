from .ApiBase import ApiBase
import logging
logger = logging.getLogger(__name__)

class PlayerApiConnector(ApiBase):
    def __init__(self, dispatch):
        ApiBase.__init__(self, '/data/player')
        self.dispatch = dispatch

    def requestDataForLeaderboard(self, leaderboardName, queryDict={}):
        self.leaderboardName = leaderboardName
        self.request(queryDict, self.handleDataForLeaderboard)

    def handleDataForLeaderboard(self, message, meta):
        preparedData = dict(
             command = 'stats'
            ,type = 'player'
            ,leaderboardName = self.leaderboardName
            ,values = message
            ,meta = meta['meta']
        )
        self.dispatch.dispatch(preparedData)