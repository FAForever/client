def test_player_equality():
    from client import Player
    assert Player(id=1, login='old_nick') == Player(id=1, login='new_nick')


def test_player_indexing():
    from client import Player
    p = Player(id=1, login='x')
    assert {1: p}[1] == {p: p}[p]
