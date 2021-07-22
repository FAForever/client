# TODO: fetch this from API

from enum import Enum


# copied from the server code according to which
# this will need be fixed when the database
# gets migrated


class RatingType(Enum):
    GLOBAL = "global"
    LADDER = "ladder_1v1"
    TMM_2v2 = "tmm_2v2"
    TMM_3v3 = "tmm_3v3"
    TMM_4v4 = "tmm_4v4"

    @staticmethod
    def fromMatchmakerQueue(matchmakerQueueName):
        for ratingType in list(RatingType):
            if ratingType.value.replace("_", "") == matchmakerQueueName:
                return ratingType.value
        return RatingType.GLOBAL.value


# this is not from the server code. but it is weird
# that rating types and leaderboard names differ
# from matchmaker queue names


class MatchmakerQueueType(Enum):
    LADDER = "ladder1v1"
    TMM_2v2 = "tmm2v2"
    TMM_3v3 = "tmm3v3"
    TMM_4v4 = "tmm4v4"

    @staticmethod
    def fromRatingType(ratingTypeName):
        for matchmakerQueue in list(MatchmakerQueueType):
            if ratingTypeName.replace("_", "") == matchmakerQueue.value:
                return matchmakerQueue.value
        return MatchmakerQueueType.LADDER.value
