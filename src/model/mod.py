class Mod():

    def __init__(self, model):
        self.model = model

    def getName(self):
        raise NotImplementedError

    def getIcon(self):
        raise NotImplementedError

    def isFeatured(self):
        raise NotImplementedError

    def getVersion(self):
        raise NotImplementedError

    # new version available
    def isOutdated(self):
        raise NotImplementedError

    def getDescription(self):
        raise NotImplementedError