from PyQt4 import QtCore
import pytest
from friendlist import FriendList

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
        return ["Anna", "Bernd", "Christoph"]


@pytest.fixture(scope="module")
def friendListModel():
    api = API_Mockup()
    friendListModel = FriendList(api)

    # view must perform model operation
    def addFriend(groupIndex, username):
        friendListModel.getGroups()[groupIndex].addUser(username, False)

    # view must perform model operation
    def removeFriend(groupIndex, username):
        friendListModel.getGroups()[groupIndex].removeUser(username)

    friendListModel.add_user.connect(addFriend)
    friendListModel.remove_user.connect(removeFriend)

    return friendListModel

def test_model(friendListModel):
    assert 0 == len(friendListModel.getGroups()[FriendList.ONLINE].users)
    assert 0 == len(friendListModel.getGroups()[FriendList.OFFLINE].users)
    # add three online players
    friendListModel.updateFriendList()
    assert 0 == len(friendListModel.getGroups()[FriendList.ONLINE].users)
    assert 3 == len(friendListModel.getGroups()[FriendList.OFFLINE].users)
    # change state to online
    friendListModel.switchUser("Bernd", FriendList.ONLINE)
    assert 1 == len(friendListModel.getGroups()[FriendList.ONLINE].users)
    assert 2 == len(friendListModel.getGroups()[FriendList.OFFLINE].users)
    # change state to offline
    friendListModel.switchUser("Bernd", FriendList.OFFLINE)
    assert 0 == len(friendListModel.getGroups()[FriendList.ONLINE].users)
    assert 3 == len(friendListModel.getGroups()[FriendList.OFFLINE].users)
    # remove friend
    friendListModel.removeUser("Bernd")
    assert 0 == len(friendListModel.getGroups()[FriendList.ONLINE].users)
    assert 2 == len(friendListModel.getGroups()[FriendList.OFFLINE].users)
    # remove twice
    friendListModel.removeUser("Bernd")
    assert 0 == len(friendListModel.getGroups()[FriendList.ONLINE].users)
    assert 2 == len(friendListModel.getGroups()[FriendList.OFFLINE].users)
    # remove a non friend
    friendListModel.removeUser("Nobody")
    assert 0 == len(friendListModel.getGroups()[FriendList.ONLINE].users)
    assert 2 == len(friendListModel.getGroups()[FriendList.OFFLINE].users)