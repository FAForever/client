import pytest

from model.ircuser import IrcUser
from model.ircuserset import IrcUserset
from model.playerset import Playerset
from model.player import Player


def test_player_change(mocker):
    ps = Playerset()
    us = IrcUserset(ps)
    u = IrcUser("Guy", "")
    us[u.name] = u
    assert u.player is None

    pUpd = mocker.Mock()
    u.newPlayer.connect(pUpd)

    p = Player(**{"id_": 1, "login": "Guy"})
    ps[p.id] = p
    pUpd.assert_called_with(u, p, None)
    assert u.player is p

    pUpd.reset_mock()
    del ps[p.id]
    pUpd.assert_called_with(u, None, p)
    assert u.player is None


def test_new_chatter():
    ps = Playerset()
    us = IrcUserset(ps)
    p = Player(**{"id_": 1, "login": "Guy"})
    ps[p.id] = p
    u = IrcUser("Guy", "")
    us[u.name] = u
    assert u.player is p


def test_chatter_rename(mocker):
    ps = Playerset()
    us = IrcUserset(ps)
    p = Player(**{"id_": 1, "login": "Guy"})
    ps[p.id] = p
    p2 = Player(**{"id_": 2, "login": "Other"})
    ps[p2.id] = p2

    u = IrcUser("Guy", "")
    us[u.name] = u

    pUpd = mocker.Mock()
    u.newPlayer.connect(pUpd)

    u.update(name="Other")
    pUpd.assert_called_with(u, p2, p)
    with pytest.raises(KeyError):
        us["Guy"]
    assert us["Other"] is u
    assert u.player is p2


def test_chatter_rename_no_player(mocker):
    ps = Playerset()
    us = IrcUserset(ps)
    p = Player(**{"id_": 1, "login": "Guy"})
    ps[p.id] = p

    u = IrcUser("Guy", "")
    us[u.name] = u

    pUpd = mocker.Mock()
    u.newPlayer.connect(pUpd)

    u.update(name="Other")
    pUpd.assert_called_with(u, None, p)
    with pytest.raises(KeyError):
        us["Guy"]
    assert us["Other"] is u
    assert u.player is None
