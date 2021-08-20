import pytest

from model.player import Player
from model.playerset import Playerset

DEFAULT_DICT = {
    "id_": 17,
    "login": "TesterNoob",
    "global_rating": (1455, 160),
    "ladder_rating": (1192, 216),
    "number_of_games": 374,
    "avatar": {
        'url': 'http://content.faforever.com/faf/avatars/GW_Cybran.png',
        'tooltip': 'Liberate !',
    },
    "country": "PL",
}


def test_add_remove(mocker):
    ps = Playerset()
    p = Player(**DEFAULT_DICT)

    def test_player_signal(sp):
        assert sp is p

    newplayer = mocker.Mock()
    goneplayer = mocker.Mock()
    ps.added.connect(newplayer)
    ps.added.connect(test_player_signal)
    ps.removed.connect(goneplayer)
    ps.removed.connect(test_player_signal)

    ps[p.id] = p
    assert newplayer.called
    assert ps[p.id] is p
    assert ps[p.login] is p

    del ps[p.id]
    assert goneplayer.called
    assert p.id not in ps
    assert p.login not in ps
    with pytest.raises(KeyError):
        ps[p.id]
    with pytest.raises(KeyError):
        ps[p.login]


def test_cant_add_by_login():
    ps = Playerset()
    p = Player(**DEFAULT_DICT)
    with pytest.raises(TypeError):
        ps[p.login] = p


def test_cant_add_twice():
    ps = Playerset()
    p = Player(**DEFAULT_DICT)
    ps[p.id] = p
    with pytest.raises(ValueError):
        ps[p.id] = p


def test_cant_add_mismatched_id():
    ps = Playerset()
    p = Player(**DEFAULT_DICT)
    ps[p.id] = p
    with pytest.raises(ValueError):
        ps[p.id + 1] = p


def test_cant_get_by_player():
    ps = Playerset()
    p = Player(**DEFAULT_DICT)
    ps[p.id] = p
    with pytest.raises(TypeError):
        ps[p]
