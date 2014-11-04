import client
from fa.replay import replay
from chat._avatarWidget import avatarWidget


class Client_Action():

    usersUpdated = None

    def __init__(self, client):
        self.client_window = client
        self.usersUpdated = self.client_window.usersUpdated

    def viewPlayerStats(self, username):
        try:
            if username in self.client_window.players :
                self.client_window.profile.setplayer(username)
                self.client_window.profile.show()
        except:
            pass

    def viewLiveReplay(self, username):
        if username in client.instance.urls:
            replay(client.instance.urls[username])

    def viewVaultReplay(self, username):
        ''' see the player replays in the vault '''
        self.client_window.replays.mapName.setText("")
        self.client_window.replays.playerName.setText(username)
        self.client_window.replays.minRating.setValue(0)
        self.client_window.replays.searchVault()
        self.client_window.mainTabs.setCurrentIndex(self.client.mainTabs.indexOf(self.client.replaysTab))

    def isFriend(self, username):
        return self.client_window.isFriend(username)

    def getCompleteUserName(self, username):
        return self.client_window.getCompleteUserName(username)

    def getUserCountry(self, username):
        return self.client_window.getUserCountry(username)

    def getUserRanking(self, username):
        return self.client_window.getUserRanking(username)

    def getUserAvatar(self, username):
        return self.client_window.getUserAvatar(username)

    def getFriends(self):
        return self.client_window.friends

    # TODO: password parameter?
    def joinInGame(self, username):
        if username in client.instance.urls:
            client.instance.joinGameFromURL(client.instance.urls[username])


    def openPrivateChat(self, chatPartner):
        # check if the client is online
        if chatPartner not in self.client_window.players:
            return
        self.client_window.changeTab(self.client_window.TAB_CHAT)
        self.client_window.chat.openQuery(chatPartner, True)

    ### social actions

    def selectAvatar(self, username):
        avatarSelection = avatarWidget(self.client_window, username, personal=True)
        avatarSelection.exec_()

    def addFriend(self, username):
        self.client_window.addFriend(username)

    def remFriend(self, username):
        self.client_window.remFriend(username)

    def addFoe(self, username):
        self.client_window.addFoe(username)

    def remFoe(self, username):
        self.client_window.remFoe(username)
