import pytest
import copy

from model import gameset, game

DEFAULT_DICT = {
    "uid": 1,
    "state": game.GameState.OPEN,
    "launched_at": 10000,
    "num_players": 3,
    "max_players": 8,
    "title": "Sentons sucks",
    "host": "IllIIIlIlIIIlI",
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


def test_add_update(mocker):
    data = copy.deepcopy(DEFAULT_DICT)
    s = gameset.Gameset()
    newgame = mocker.Mock()
    s.newGame.connect(newgame)

    s.update_set(data)
    assert 1 in s
    g = s[1]
    newgame.assert_called_with(g)
    newgame.reset_mock()

    data["title"] = "Something"
    s.update_set(data)
    assert 1 in s
    assert g is s[1]
    assert not newgame.called
    newgame.reset_mock()

    data["uid"] = 2
    s.update_set(data)
    assert 2 in s
    g2 = s[2]
    assert g is not g2
    newgame.assert_called_with(g2)


def test_fail_to_add(mocker):
    s = gameset.Gameset()
    newgame = mocker.Mock()
    s.newGame.connect(newgame)

    s.update_set({"uid": 1})
    assert not newgame.called
    assert 1 not in s
    with pytest.raises(KeyError):
        g = s[1]


def test_fail_to_add_no_uid(mocker):
    s = gameset.Gameset()
    newgame = mocker.Mock()
    s.newGame.connect(newgame)

    s.update_set({"uid": 1})
    assert not newgame.called
    assert 1 not in s
    with pytest.raises(KeyError):
        g = s[1]


def test_abort_at_bad_update(mocker):
    s = gameset.Gameset()
    data = copy.deepcopy(DEFAULT_DICT)
    s.update_set(data)

    g = s[1]
    closed = mocker.Mock()
    g.gameClosed.connect(closed)

    del data["state"]
    s.update_set(data)

    assert closed.called
    assert 1 not in s
    with pytest.raises(KeyError):
        g = s[1]


def test_iter():
    s = gameset.Gameset()
    data = copy.deepcopy(DEFAULT_DICT)
    s.update_set(data)

    num = 0
    for g in s:
        assert g is s[1]
        num += 1
    assert num == 1


def test_clear():
    s = gameset.Gameset()
    data = copy.deepcopy(DEFAULT_DICT)
    s.update_set(data)
    s.clear_set()

    num = 0
    for g in s:
        num += 1
    assert num == 0


def test_new_states_one_object(mocker):
    s = gameset.Gameset()
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

    s.update_set(data)
    assert lobby.called
    assert not live.called
    assert not closed.called
    reset()

    data["state"] = game.GameState.PLAYING
    s.update_set(data)
    assert not lobby.called
    assert live.called
    assert not closed.called
    reset()

    data["state"] = game.GameState.CLOSED
    s.update_set(data)
    assert not lobby.called
    assert not live.called
    assert closed.called


def test_new_states_new_objects(mocker):
    s = gameset.Gameset()
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

    s.update_set(data)
    assert lobby.called
    assert not live.called
    assert not closed.called
    reset()

    data["uid"] = 2
    data["state"] = game.GameState.PLAYING
    s.update_set(data)
    assert not lobby.called
    assert live.called
    assert not closed.called
    reset()

    data["uid"] = 3
    data["state"] = game.GameState.CLOSED
    s.update_set(data)
    assert not lobby.called
    assert not live.called
    # A new closed game does *not* get reported.
    assert not closed.called


def test_no_state_changes(mocker):
    s = gameset.Gameset()
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

    s.update_set(data)
    reset()
    data['title'] = "New"
    s.update_set(data)
    assert not lobby.called
    assert not live.called
    assert not closed.called
