import pytest

from model.ircuser import IrcUser
from model.ircuserset import IrcUserset


@pytest.fixture
def playerset(mocker):
    return mocker.MagicMock()


def test_add_remove(playerset, mocker):
    ps = IrcUserset(playerset)
    p = IrcUser("Name", "Hostname")

    def test_user_signal(sp):
        assert sp is p

    newuser = mocker.Mock()
    goneuser = mocker.Mock()
    ps.added.connect(newuser)
    ps.added.connect(test_user_signal)
    ps.removed.connect(goneuser)
    ps.removed.connect(test_user_signal)

    ps[p.name] = p
    assert newuser.called
    assert ps[p.name] is p

    del ps[p.name]
    assert goneuser.called
    assert p.name not in ps
    with pytest.raises(KeyError):
        ps[p.name]


def test_cant_add_twice(playerset):
    ps = IrcUserset(playerset)
    p = IrcUser("Name", "Hostname")
    ps[p.name] = p
    with pytest.raises(ValueError):
        ps[p.name] = p


def test_cant_add_mismatched_name(playerset):
    ps = IrcUserset(playerset)
    p = IrcUser("Name", "Hostname")
    ps[p.name] = p
    with pytest.raises(ValueError):
        ps[p.name + "Other"] = p
