import copy

from model.game import Game, GameState, GameVisibility
from model.gameset import Gameset, PlayerGameIndex
from model.playerset import Playerset
from model.player import Player

GAME_DICT = {
    "uid":  1,
    "state": GameState.OPEN,
    "launched_at": 10000,
    "num_players": 3,
    "max_players": 8,
    "title": "Sentons sucks",
    "host":  "Guy",
    "mapname": "Sentons Ultimate 6v6",
    "map_file_path": "xrca_co_000001.scfamap",
    "teams": {
        1: ["Guy", "TableNoob"],
        2: ["Kraut"]
        },
    "featured_mod": "faf",
    "sim_mods": {},
    "password_protected": False,
    "visibility": GameVisibility.PUBLIC,
}


def check_relation(game, player, exists):
    assert (player.currentGame is game) == exists
    assert game.is_ingame(player.login) == exists


def setup():
    ps = Playerset()
    gs = Gameset(ps)
    pgr = PlayerGameIndex(gs, ps)
    p = Player(**{"id_": 1, "login": "Guy"})
    ps[p.id] = p
    p = Player(**{"id_": 2, "login": "TableNoob"})
    ps[p.id] = p
    p = Player(**{"id_": 3, "login": "Kraut"})
    ps[p.id] = p

    g = Game(playerset=ps, **GAME_DICT)
    gs[g.uid] = g
    return ps, gs, pgr


def test_setup():
    ps, gs, pgr = setup()
    for i in range(1, 3):
        assert ps[i].currentGame is gs[1]

    gps = [gs[1].to_player(n) for n in gs[1].players if gs[1].is_connected(n)]
    assert len(gps) == 3
    for i in range(1, 3):
        assert ps[1] in gps

    gps = [gs[1].to_player(n) for n in gs[1].players if gs[1].is_ingame(n)]
    assert len(gps) == 3
    for i in range(1, 3):
        assert ps[1] in gps


def test_player_at_game_change(mocker):
    ps = Playerset()
    gs = Gameset(ps)
    pgr = PlayerGameIndex(gs, ps)

    p = Player(**{"id_": 1, "login": "Guy"})
    ps[p.id] = p
    p = Player(**{"id_": 2, "login": "TableNoob"})
    ps[p.id] = p
    p = Player(**{"id_": 3, "login": "Kraut"})
    ps[p.id] = p

    data = copy.deepcopy(GAME_DICT)
    g1 = Game(playerset=ps, **data)

    gUpd = mocker.Mock()
    ps[1].newCurrentGame.connect(gUpd)

    gs[1] = g1
    gUpd.assert_called_with(ps[1], g1, None)
    gUpd.reset_mock()

    data["state"] = GameState.PLAYING
    gs[1].update(**data)

    assert not gUpd.called

    data["state"] = GameState.CLOSED
    gs[1].update(**data)
    gUpd.assert_called_with(ps[1], None, g1)


def test_player_at_another_game(mocker):
    ps, gs, pgr = setup()

    data = copy.deepcopy(GAME_DICT)

    # Game starts
    data["state"] = GameState.PLAYING
    gs[1].update(**data)

    data["state"] = GameState.OPEN
    data["uid"] = 2
    data["teams"] = {1: ["Guy"]}
    g2 = Game(playerset=ps, **data)

    gUpd = mocker.Mock()
    ps[1].newCurrentGame.connect(gUpd)

    gs[2] = g2
    gUpd.assert_called_with(ps[1], g2, gs[1])
    gUpd.reset_mock()

    # Test if closing the first game changes player state
    data = copy.deepcopy(GAME_DICT)
    data["state"] = GameState.CLOSED
    gs[1].update(**data)
    assert not gUpd.called


def test_game_at_missing_player(mocker):
    ps = Playerset()
    gs = Gameset(ps)
    pgr = PlayerGameIndex(gs, ps)

    p = Player(**{"id_": 1, "login": "Guy"})
    ps[p.id] = p
    p = Player(**{"id_": 2, "login": "TableNoob"})
    ps[p.id] = p

    data = copy.deepcopy(GAME_DICT)
    g1 = Game(playerset=ps, **data)

    gs[1] = g1
    assert len(g1.players) == 3
    gps = [g1.to_player(n) for n in g1.players if g1.is_connected(n)]
    assert len(gps) == 2
    assert ps[1] in gps
    assert ps[2] in gps

    p = Player(**{"id_": 3, "login": "Kraut"})
    ps[p.id] = p

    gps = [g1.to_player(n) for n in g1.players if g1.is_connected(n)]
    assert len(gps) == 3
    assert ps[3] in gps
    assert g1.is_ingame(ps[3].login)
    assert ps[3].currentGame is g1


def test_remove_add_player(mocker):
    ps, gs, pgr = setup()
    p3 = ps[3]
    del ps[3]
    assert not gs[1].is_connected(p3.login)
    ps[3] = p3
    assert gs[1].is_connected(p3.login)


def test_game_at_another_game(mocker):
    ps, gs, pgr = setup()

    data = copy.deepcopy(GAME_DICT)

    # Game starts
    data["state"] = GameState.PLAYING
    gs[1].update(**data)

    data["state"] = GameState.OPEN
    data["uid"] = 2
    data["teams"] = {1: ["Guy"]}
    g2 = Game(playerset=ps, **data)

    pRem = mocker.Mock()
    gs[1].ingamePlayerRemoved.connect(pRem)

    gs[2] = g2
    pRem.assert_called_with(gs[1], ps[1])

    check_relation(gs[1], ps[1], False)


def test_no_player_change_does_not_resend_game_set_signals(mocker):
    ps, gs, pgr = setup()

    gUpd = mocker.Mock()
    ps[1].newCurrentGame.connect(gUpd)

    data = copy.deepcopy(GAME_DICT)
    data["state"] = GameState.PLAYING
    gs[1].update(**data)
    assert not gUpd.called


def test_game_abort_removes_relation(mocker):
    ps, gs, pgr = setup()
    gUpd = mocker.Mock()
    ps[1].newCurrentGame.connect(gUpd)

    g1 = gs[1]
    gs[1].abort_game()
    gUpd.assert_called_with(ps[1], None, g1)
    for i in range(1, 3):
        assert ps[i].currentGame is None
    assert [p for p in g1.players if g1.is_ingame(p)] == []


def test_game_closed_removes_relation(mocker):
    ps, gs, pgr = setup()
    gUpd = mocker.Mock()
    ps[1].newCurrentGame.connect(gUpd)

    data = copy.deepcopy(GAME_DICT)
    data["state"] = GameState.CLOSED

    g1 = gs[1]
    gs[1].update(**data)

    gUpd.assert_called_with(ps[1], None, g1)
    for i in range(1, 3):
        assert ps[i].currentGame is None
    assert [p for p in g1.players if g1.is_ingame(p)] == []


def test_game_closed_removes_only_own(mocker):
    ps, gs, pgr = setup()

    data = copy.deepcopy(GAME_DICT)
    data["uid"] = 2
    data["teams"] = {1: ["Guy"]}
    g2 = Game(playerset=ps, **data)
    gs[2] = g2

    data = copy.deepcopy(GAME_DICT)
    data["state"] = GameState.CLOSED
    gs[1].update(**data)

    assert ps[1].currentGame is gs[2]
    assert ps[2].currentGame is None
    assert ps[3].currentGame is None


def override_tests(g1_dict, g2_dict, should):
    ps, gs, pgr = setup()

    data = copy.deepcopy(GAME_DICT)
    data.update(g1_dict)
    gs[1].update(**data)

    data = copy.deepcopy(GAME_DICT)
    data["uid"] = 2
    data["teams"] = {1: ["Guy"]}
    data.update(g2_dict)

    g2 = Game(playerset=ps, **data)
    gs[2] = g2
    check_relation(gs[2], ps[1], should)


def test_lobby_overrides_game_players():
    g1 = {"state": GameState.PLAYING}
    g2 = {"state": GameState.OPEN}
    override_tests(g1, g2, True)


def test_game_doesnt_override_lobby():
    g1 = {"state": GameState.PLAYING}
    g2 = {"state": GameState.OPEN}
    override_tests(g1, g2, True)


def test_later_game_overrides_earlier_game():
    g1 = {"state": GameState.PLAYING,
          "launched_at": 1000}
    g2 = {"state": GameState.PLAYING,
          "launched_at": 1200}
    override_tests(g1, g2, True)


def test_earlier_game_doesnt_override_later_game():
    g1 = {"state": GameState.PLAYING,
          "launched_at": 1200}
    g2 = {"state": GameState.PLAYING,
          "launched_at": 1000}
    override_tests(g1, g2, False)


def test_launchtime_overrides_no_launchtime():
    g1 = {"state": GameState.PLAYING,
          "launched_at": None}
    g2 = {"state": GameState.PLAYING,
          "launched_at": 1000}
    override_tests(g1, g2, True)


def test_no_launchtime_doesnt_override_launchtime():
    g1 = {"state": GameState.PLAYING,
          "launched_at": 1000}
    g2 = {"state": GameState.PLAYING,
          "launched_at": None}
    override_tests(g1, g2, False)
