def conservative_estimate(rating):
    return rating[0]-(3*rating[1])


def test_average_rating(qtbot):
    import config
    config.no_dialogs = True
    import client
    from client import Player
    from games.gameitem import GameItem
    players = [Player(id=1, login='Test-1', global_rating=(2000, 200)),
              Player(id=2, login='Test-2', global_rating=(1000, 150)),
              Player(id=3, login='Test-3', global_rating=(1200, 100))]
    g = GameItem(0)
    client.players = dict([(p.id, p) for p in players])
    g.client = client
    g.players = players

    expected_average_rating = sum([conservative_estimate(p.global_rating) for p in players]) / len(players)
    assert expected_average_rating == g.average_rating


def test_average_rating_no_players(qtbot):
    import config
    config.no_dialogs = True
    import client
    from games.gameitem import GameItem
    players = []
    g = GameItem(0)
    client.players = dict([(p.id, p) for p in players])
    g.client = client
    g.players = players

    assert 0 == g.average_rating
