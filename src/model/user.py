class User():

    def __init__(self, model):
        self.model = model

    def getAvatar(self):
        raise NotImplementedError

    def setAvatar(self, avatar):
        raise NotImplementedError

    def getRating(self):
        raise NotImplementedError

    def getNick(self):
        raise NotImplementedError

    def getClan(self):
        raise NotImplementedError

    def getNmeWithClantag(self):
        raise NotImplementedError

    def getFriends(self):
        raise NotImplementedError

    def isFriends(self):
        raise NotImplementedError

    def addFriend(self, user):
        raise NotImplementedError

    def removeFriend(self):
        raise NotImplementedError

    def getFoes(self):
        raise NotImplementedError

    def isFoe(self):
        raise NotImplementedError

    def addFoe(self, user):
        raise NotImplementedError

    def removeFoe(self, user):
        raise NotImplementedError

    # control - seperate into control?
    def joinGame(self, game):
        raise NotImplementedError

    def viewLiveReplay(self, replay):
        raise NotImplementedError

    def viewVaultReplay(self, replay):
        raise NotImplementedError

    def showStats(self, replay):
        raise NotImplementedError
