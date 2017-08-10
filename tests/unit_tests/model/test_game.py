import pytest
import copy

from model import game

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


def test_simple_correct_init():
    g = game.Game(**DEFAULT_DICT)


def test_uid_required_for_init():
    data = copy.deepcopy(DEFAULT_DICT)
    del data["uid"]
    with pytest.raises(game.BadUpdateException):
        g = game.Game(**data)


def test_wrong_uid_for_update():
    data = copy.deepcopy(DEFAULT_DICT)
    g = game.Game(**data)
    data["uid"] = 2
    with pytest.raises(game.BadUpdateException):
        g.update(**data)


def general_invalid_dict(dict_):
    with pytest.raises(game.BadUpdateException):
        g = game.Game(**dict_)
    g = game.Game(**DEFAULT_DICT)
    with pytest.raises(game.BadUpdateException):
        g.update(**dict_)


def test_invalid_gamestate():
    data = copy.deepcopy(DEFAULT_DICT)
    data["state"] = "AAAAA"
    general_invalid_dict(data)


def test_invalid_visibility():
    data = copy.deepcopy(DEFAULT_DICT)
    i = 0
    while i in game.GameVisibility:
        i += 1
    data["visibility"] = i
    general_invalid_dict(data)


def test_update_signal(mocker):
    data = copy.deepcopy(DEFAULT_DICT)
    g = game.Game(**data)
    updated = mocker.Mock()
    g.gameUpdated.connect(updated)
    data["host"] = "OtherName"
    g.update(**data)
    assert updated.called


def test_close_signals(mocker):
    data = copy.deepcopy(DEFAULT_DICT)
    g = game.Game(**data)
    updated = mocker.Mock()
    g.gameUpdated.connect(updated)
    closed = mocker.Mock()
    g.gameClosed.connect(closed)
    data["state"] = game.GameState.CLOSED
    g.update(**data)
    assert updated.called
    assert closed.called


def test_closed_determined_by_gamestate():
    data = copy.deepcopy(DEFAULT_DICT)

    g = game.Game(**data)
    assert not g.closed()
    g.update(**data)
    assert not g.closed()
    data["state"] = game.GameState.PLAYING
    g.update(**data)
    assert not g.closed()
    data["state"] = game.GameState.CLOSED
    g.update(**data)
    assert g.closed()


def test_abort_closes(mocker):
    data = copy.deepcopy(DEFAULT_DICT)
    g = game.Game(**data)
    closed = mocker.Mock()
    g.gameClosed.connect(closed)
    assert not g.closed()

    g.abort_game()
    assert g.closed()
    assert closed.called


def test_cannot_update_closed():
    data = copy.deepcopy(DEFAULT_DICT)
    g = game.Game(**data)
    g.abort_game()
    with pytest.raises(game.BadUpdateException):
        g.update(data)


def test_state_change_signals(mocker):
    data = copy.deepcopy(DEFAULT_DICT)
    g = game.Game(**data)
    change = mocker.Mock()
    g.newState.connect(change)

    data["state"] = game.GameState.PLAYING
    g.update(**data)
    change.assert_called_with(g)
    change.reset_mock()

    data["state"] = game.GameState.CLOSED
    g.update(**data)
    change.assert_called_with(g)


def test_abort_does_not_change_state(mocker):
    data = copy.deepcopy(DEFAULT_DICT)
    g = game.Game(**data)
    change = mocker.Mock()
    g.newState.connect(change)

    g.abort_game()
    assert not change.called


def test_no_state_changes(mocker):
    data = copy.deepcopy(DEFAULT_DICT)
    g = game.Game(**data)
    change = mocker.Mock()
    g.newState.connect(change)
    data['title'] = "New"
    g.update(**data)

    assert not change.called
