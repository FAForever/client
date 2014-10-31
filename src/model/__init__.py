from PyQt4 import QtCore

class Model(QtCore.QObject):
    # General
    friendGroupCreated = QtCore.pyqtSignal(object)  # friendgroup

    # User
    friendAdded = QtCore.pyqtSignal(object, object)  # user, newfriend
    friendRemoved = QtCore.pyqtSignal(object, object, object)  # user, oldfriend
    foeAdded = QtCore.pyqtSignal(object, object, object)  # user, newfoe
    foeRemoved = QtCore.pyqtSignal(object, object, object)  # user, oldfoe
    gameJoined = QtCore.pyqtSignal(object, object, object)  # user, game
    viewLiveReplay = QtCore.pyqtSignal(object, object, object)  # user, replay
    viewVaultReplay = QtCore.pyqtSignal(object, object, object)  # user, replay
    statsShowed = QtCore.pyqtSignal(object, object, object)  # user

    # Game
    gameModChanged = QtCore.pyqtSignal(object, object)  # game, newmod
    gameMapChanged = QtCore.pyqtSignal(object, object, object)  # game, newmap, oldmap
    gameMinRatingChanged = QtCore.pyqtSignal(object, object)  # game, new, old
    gameMaxRatingChanged = QtCore.pyqtSignal(object, object)  # game, new, old
    gameBalanceChanged = QtCore.pyqtSignal(object, object, object)  # game, new, old
    gamePlayerCountChanged = QtCore.pyqtSignal(object, object, object)  # game, new, old
    gameSettingsChanged = QtCore.pyqtSignal(object, object, object)  # game, new, old

    # Frien Group
    friendGroupUserAdded = QtCore.pyqtSignal(object, object)  # friendgroup, newUser
    friendGroupUserRemoved = QtCore.pyqtSignal(object, object)  # friendgroup, oldUser
    friendGroupRemoved = QtCore.pyqtSignal(object)  # friendgroup

    # Map
    mapNewVersionAvailable = QtCore.pyqtSignal(object)  # map

    # Mod
    modNewVersionAvailable = QtCore.pyqtSignal(object)  # mod

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
