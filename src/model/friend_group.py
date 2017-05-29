class FriendGroup():

    def __init__(self, model):
        self.model = model

    def getName(self):
        raise NotImplementedError

    def getUsers(self):
        raise NotImplementedError

    def addUser(self, user):
        raise NotImplementedError

    def removeUser(self, user):
        raise NotImplementedError

    def rename(self, newName):
        raise NotImplementedError

    def remove(self):
        raise NotImplementedError