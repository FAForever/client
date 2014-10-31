class FriendGroup():
    def getName(self):
        raise NotImplementedError

    def setName(self, name):
        raise NotImplementedError

    def getUsers(self):
        raise NotImplementedError

    def addUser(self, user):
        raise NotImplementedError

    def removeUser(self, user):
        raise NotImplementedError

    def rename(self, newName):
        raise NotImplementedError