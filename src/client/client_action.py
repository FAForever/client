import client
from fa.replay import replay


class Client_Action():

    def __init__(self, client):
        self.client_window = client

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

    # TODO: password parameter?
    def joinInGame(self, username):
        if username in client.instance.urls:
            client.instance.joinGameFromURL(client.instance.urls[username])