class User():
    GAMESTATUS_HOST = 'host'
    GAMESTATUS_LOBBY = 'lobby'
    GAMESTATUS_INGAME = 'ingame'
    GAMESTATUS_LIVEREPLAY = 'livereplay'
    GAMESTATUS_VAULTREPLAY = 'vaultreplay'

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
        '''
        Returns a user's clan if any
        '''
        raise NotImplementedError

    def getNameWithClantag(self):
        raise NotImplementedError

    def getFriends(self):
        raise NotImplementedError

    def isFriend(self, user):
        '''
        Convenience function for other modules to inquire about a user's friendliness.
        '''
        raise NotImplementedError

    def addFriend(self, user):
        raise NotImplementedError

    def removeFriend(self, user):
        raise NotImplementedError

    def getFoes(self):
        raise NotImplementedError

    def isFoe(self):
        '''
        Convenience function for other modules to inquire about a user's foeliness.
        '''
        raise NotImplementedError

    def addFoe(self, user):
        raise NotImplementedError

    def removeFoe(self, user):
        raise NotImplementedError

    def isOnline(self):
        raise NotImplementedError

    def getGameStats(self):
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

    def getCountry(self):
        '''
        Returns a user's country if any
        '''
        raise NotImplementedError

    def getColor(self):
        raise NotImplementedError

    def getStatusColor(self):
        '''
        Returns a user's color depending on their status with relation to the FAF client
        '''
        raise NotImplementedError

    def getRandomColor(self):
        '''Generate a random color from a name'''
        raise NotImplementedError

class Country():
    def getShortName(self):
        raise NotImplementedError

    def getFullName(self):
        raise NotImplementedError

    def getIcon(self):
        raise NotImplementedError