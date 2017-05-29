class Game():
    GAMESTATE_OPEN = 'open'
    GAMESTATE_CLOSED = 'closed'

    GAMETYPE_PUBLIC = 'public'
    GAMETYPE_PASSWORD = 'password'
    GAMETYPE_GW = 'GW'

    def __init__(self, model):
        self.model = model

    def getUid(self):
        raise NotImplementedError

    def getState(self):
        raise NotImplementedError

    def getType(self):
        raise NotImplementedError

    def getName(self):
        raise NotImplementedError

    def getFeatureMod(self):
        raise NotImplementedError

    def getMods(self):
        raise NotImplementedError

    def getStartedTime(self):
        raise NotImplementedError

    def changeMod(self, newMods):
        raise NotImplementedError

    def getMap(self):
        raise NotImplementedError

    def getMinRating(self):
        raise NotImplementedError

    def changeMinRating(self, minRating):
        raise NotImplementedError

    def getMaxRating(self):
        raise NotImplementedError

    def changeMaxRating(self, maxRating):
        raise NotImplementedError

    def getHoster(self):
        raise NotImplementedError

    def getGameSettings(self):
        raise NotImplementedError

    def getCurrentPlayerCount(self):
        raise NotImplementedError

    def getGameBalance(self):
        raise NotImplementedError

class GameSetting():
    def hasUnitRestriction(self):
        raise NotImplementedError

    def getActiveUnitRestrictions(self):
        raise NotImplementedError

    # TODO: add faf options?