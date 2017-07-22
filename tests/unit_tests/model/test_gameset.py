import pytest
import copy

from model import gameset, game

DEFAULT_DICT = {
    "uid":  1,
    "state": game.GameState.OPEN,
    "launched_at": 10000,
    "num_players": 3,
    "max_players": 8,
    "title": "Sentons sucks",
    "host":  "IllIIIlIlIIIlI",
    "mapname": "Sentons Ultimate 6v6",
    "map_file_path": "xrca_co_000001.scfamap",
    "teams": {
        1: ["IllIIIlIlIIIlI", "TableNoob"],
        2: ["Kraut"]
        },
    "featured_mod": "faf",
    "featured_mod_versions": {},
    "sim_mods": {},
    "password_protected": False,
    "visibility": game.GameVisibility.PUBLIC,
}


@pytest.fixture
def playerset(mocker):
    return mocker.MagicMock()


def test_add_update(mocker, playerset):
    data = copy.deepcopy(DEFAULT_DICT)
    s = gameset.Gameset(playerset=playerset)
    newgame = mocker.Mock()
    s.newGame.connect(newgame)

    s[1] = game.Game(playerset=playerset, **data)
    assert 1 in s
    g = s[1]
    newgame.assert_called_with(g)
    newgame.reset_mock()

    data["title"] = "Something"
    s[1].update(**data)
    assert 1 in s
    assert g is s[1]
    assert not newgame.called
    newgame.reset_mock()

    data["uid"] = 2
    s[2] = game.Game(playerset=playerset, **data)
    assert 2 in s
    g2 = s[2]
    assert g is not g2
    newgame.assert_called_with(g2)


def test_iter(playerset):
    s = gameset.Gameset(playerset=playerset)
    data = copy.deepcopy(DEFAULT_DICT)
    s[1] = game.Game(playerset=playerset, **data)

    num = 0
    for g in s.values():
        assert g is s[1]
        num += 1
    assert num == 1


def test_clear(playerset):
    s = gameset.Gameset(playerset=playerset)
    data = copy.deepcopy(DEFAULT_DICT)
    s[1] = game.Game(playerset=playerset, **data)
    s.clear()

    num = 0
    for g in s:
        num += 1
    assert num == 0


def test_new_states_one_object(playerset, mocker):
    s = gameset.Gameset(playerset=playerset)
    lobby = mocker.Mock()
    live = mocker.Mock()
    closed = mocker.Mock()
    s.newLobby.connect(lobby)
    s.newLiveGame.connect(live)
    s.newClosedGame.connect(closed)

    def reset():
        lobby.reset_mock()
        live.reset_mock()
        closed.reset_mock()
    data = copy.deepcopy(DEFAULT_DICT)

    g = game.Game(playerset=playerset, **data)
    s[1] = g
    assert lobby.called
    assert not live.called
    assert not closed.called
    reset()

    data["state"] = game.GameState.PLAYING
    s[1].update(**data)
    assert not lobby.called
    assert live.called
    assert not closed.called
    reset()

    data["state"] = game.GameState.CLOSED
    s[1].update(**data)
    assert not lobby.called
    assert not live.called
    assert closed.called


def test_new_states_new_objects(playerset, mocker):
    s = gameset.Gameset(playerset=playerset)
    lobby = mocker.Mock()
    live = mocker.Mock()
    closed = mocker.Mock()
    s.newLobby.connect(lobby)
    s.newLiveGame.connect(live)
    s.newClosedGame.connect(closed)

    def reset():
        lobby.reset_mock()
        live.reset_mock()
        closed.reset_mock()
    data = copy.deepcopy(DEFAULT_DICT)
    data["uid"] = 1

    s[1] = game.Game(playerset=playerset, **data)
    assert lobby.called
    assert not live.called
    assert not closed.called
    reset()

    data["uid"] = 2
    data["state"] = game.GameState.PLAYING
    s[2] = game.Game(playerset=playerset, **data)
    assert not lobby.called
    assert live.called
    assert not closed.called
    reset()

    data["uid"] = 3
    data["state"] = game.GameState.CLOSED
    with pytest.raises(ValueError):
        s[3] = game.Game(playerset=playerset, **data)
    assert not lobby.called
    assert not live.called
    # A new closed game does *not* get reported.
    assert not closed.called


def test_no_state_changes(playerset, mocker):
    s = gameset.Gameset(playerset=playerset)
    lobby = mocker.Mock()
    live = mocker.Mock()
    closed = mocker.Mock()
    s.newLobby.connect(lobby)
    s.newLiveGame.connect(live)
    s.newClosedGame.connect(closed)

    def reset():
        lobby.reset_mock()
        live.reset_mock()
        closed.reset_mock()
    data = copy.deepcopy(DEFAULT_DICT)

    s[1] = game.Game(playerset=playerset, **data)
    reset()
    data['title'] = "New"
    s[1].update(**data)
    assert not lobby.called
    assert not live.called
    assert not closed.called
