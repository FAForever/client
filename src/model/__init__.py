class Model():
    def getUser(self, username):
        raise NotImplementedError

    def getGame(self, gameid):
        raise NotImplementedError

    def getAllInstalledMaps(self):
        raise NotImplementedError

    def getMap(self, name):
        raise NotImplementedError

    def getAllInstalledMods(self):
        raise NotImplemented

    def getAllFeaturesMods(self):
        raise NotImplemented

    def getMod(self, modname):
        raise NotImplementedError

    def createNewFriendGroup(self, newGroupName):
        raise NotImplementedError

    # TODO: host game