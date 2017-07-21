from model import game
from model.player import Player

DEFAULT_GAMEDICT = {
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

def conservative_estimate(rating):
    return rating[0]-(3*rating[1])


def test_average_rating(mocker, qtbot):
    import config
    config.no_dialogs = True
    import client
    from games.gameitem import GameItem
    players = [Player(id_=1, login='Test-1', global_rating=(2000, 200)),
              Player(id_=2, login='Test-2', global_rating=(1000, 150)),
              Player(id_=3, login='Test-3', global_rating=(1200, 100))]
    g = GameItem(game.Game(playerset = mocker.Mock(), **DEFAULT_GAMEDICT))
    client.players = dict([(p.id, p) for p in players])
    g.client = client
    g.players = players

    expected_average_rating = sum([conservative_estimate(p.global_rating) for p in players]) / len(players)
    assert expected_average_rating == g.average_rating


def test_average_rating_no_players(mocker, qtbot):
    import config
    config.no_dialogs = True
    import client
    from games.gameitem import GameItem
    players = []
    g = GameItem(game.Game(playerset = mocker.Mock(), **DEFAULT_GAMEDICT))
    client.players = dict([(p.id, p) for p in players])
    g.client = client
    g.players = players

    assert 0 == g.average_rating
