import pytest
import copy

from model import game

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

def test_simple_correct_init(playerset):
    g = game.Game(playerset=playerset, **DEFAULT_DICT)

def test_uid_required_for_init(playerset):
    data = copy.deepcopy(DEFAULT_DICT)
    del data["uid"]
    with pytest.raises(TypeError):
        g = game.Game(playerset=playerset, **data)

def test_update_signal(playerset, mocker):
    data = copy.deepcopy(DEFAULT_DICT)
    g = game.Game(playerset=playerset, **data)
    updated = mocker.Mock()
    g.gameUpdated.connect(updated)
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
