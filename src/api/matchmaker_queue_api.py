import logging

from .ApiBase import ApiBase

logger = logging.getLogger(__name__)


class matchmakerQueueApiConnector(ApiBase):
    def __init__(self, dispatch):
        ApiBase.__init__(self, '/data/matchmakerQueue')
        self.dispatch = dispatch

    def requestData(self, queryDict={}):
        self.request(queryDict, self.handleData)

    def handleData(self, message):
        preparedData = {
            "command": "matchmaker_queue_info",
            "values": [],
        }
        for queue in message:
            preparedQueue = {
                "technicalName": queue["technicalName"],
                "ratingType": queue["leaderboard"]["technicalName"],
                "id": queue["id"],
                "leaderboardId": queue["leaderboard"]["id"],
            }
            preparedData["values"].append(preparedQueue)
        self.dispatch.dispatch(preparedData)
