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
        2: ["Kraut"],
    },
    "featured_mod": "faf",
    "sim_mods": {},
    "password_protected": False,
    "visibility": game.GameVisibility.PUBLIC,
}


def test_simple_correct_init(playerset):
    game.Game(playerset=playerset, **DEFAULT_DICT)


def test_uid_required_for_init(playerset):
    data = copy.deepcopy(DEFAULT_DICT)
    del data["uid"]
    with pytest.raises(TypeError):
        game.Game(playerset=playerset, **data)


def test_update_signal(playerset, mocker):
    data = copy.deepcopy(DEFAULT_DICT)
    g = game.Game(playerset=playerset, **data)
    updated = mocker.Mock()

    def check_signal(new, old):
        assert old.host == "IllIIIlIlIIIlI"
        assert new.host == "OtherName"

    g.updated.connect(updated)
    g.updated.connect(check_signal)
    data["host"] = "OtherName"
    g.update(**data)
    assert updated.called


def test_closed_determined_by_gamestate(playerset):
    data = copy.deepcopy(DEFAULT_DICT)

    g = game.Game(playerset=playerset, **data)
    assert not g.closed()
    g.update(**data)
    assert not g.closed()
    data["state"] = game.GameState.PLAYING
    g.update(**data)
    assert not g.closed()
    data["state"] = game.GameState.CLOSED
    g.update(**data)
    assert g.closed()


def test_abort_closes(playerset, mocker):
    data = copy.deepcopy(DEFAULT_DICT)
    g = game.Game(playerset=playerset, **data)
    assert not g.closed()
    g.abort_game()
    assert g.closed()


def test_copy(playerset, mocker):
    data = copy.deepcopy(DEFAULT_DICT)
    g = game.Game(playerset=playerset, **data)
    gc = g.copy()
    assert g.to_dict() == gc.to_dict()


def test_can_update_partially(playerset, mocker):
    data = copy.deepcopy(DEFAULT_DICT)
    g = game.Game(playerset=playerset, **data)
    d1 = g.to_dict()
    g.update(launched_at=20000)
    d2 = g.to_dict()

    assert d2["launched_at"] == 20000
    del d1["launched_at"]
    del d2["launched_at"]
    assert d1 == d2


def test_can_update_to_none(playerset, mocker):
    data = copy.deepcopy(DEFAULT_DICT)
    g = game.Game(playerset=playerset, **data)
    g.update(launched_at=None)
    assert g.launched_at is None
