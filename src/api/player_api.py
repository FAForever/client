import logging

from .ApiBase import ApiBase

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
            command='stats',
            type='player',
            leaderboardName=self.leaderboardName,
            values=message,
            meta=meta['meta'],
        )
        self.dispatch.dispatch(preparedData)

    def requestDataForAliasViewer(self, nameToFind):
        queryDict = {
            'include': 'names',
            'filter': '(login=="{name}",names.name=="{name}")'.format(
                name=nameToFind,
            ),
            'fields[player]': 'login,names',
            'fields[nameRecord]': 'name,changeTime,player',
        }
        self.request(queryDict, self.handleDataForAliasViewer)

    def handleDataForAliasViewer(self, message, meta=None):
        preparedData = dict(
            command='alias_info',
            values=message,
        )
        self.dispatch.dispatch(preparedData)
