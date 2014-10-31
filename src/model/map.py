class Map():

    def __init__(self, model):
        self.model = model

    def getName(self):
        raise NotImplementedError

    def getFullName(self):
        raise NotImplementedError

    def getSize(self):
        raise NotImplementedError

    def getPreview(self):
        raise NotImplementedError

    def getMexCount(self):
        raise NotImplementedError

    def getEnergyCount(self):
        raise NotImplementedError

    def getPlayerCount(self):
        raise NotImplementedError

    def getVersion(self):
        raise NotImplementedError

    # new version available
    def isOutdated(self):
        raise NotImplementedError