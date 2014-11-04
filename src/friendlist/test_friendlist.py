from PyQt4 import QtCore
import pytest
from . import FriendList

__author__ = 'Dragonfire'


class API_Mockup(QtCore.QObject):

    usersUpdated = QtCore.pyqtSignal(dict)


    def isFriend(self, username):
        return True

    def getCompleteUserName(self, username):
        return username

    def getUserCountry(self, username):
        return "DE"

    def getUserRanking(self, username):
        return 1337

    def getUserAvatar(self, username):
        return None

    def getFriends(self):
        return []

@pytest.fixture(scope="module")
def api():
    return API_Mockup()

def test_model(api):
    friendListModel = FriendList(api)
    # add three online players
    friendListModel.addUser("Anna")
    friendListModel.addUser("Bernd")
    friendListModel.addUser("Christoph")
    assert 3 == len(friendListModel.users)
    # change state to offline
    friendListModel.addUser("Bernd")
    assert 3 == len(friendListModel.users)
    # remove friend
    friendListModel.removeFriend("Bernd")
    assert 2 == len(friendListModel.users)
    # remove twice
    friendListModel.removeFriend("Bernd")
    assert 2 == len(friendListModel.users)
    # remove a non friend
    friendListModel.removeFriend("Nobody")
    assert 2 == len(friendListModel.users)