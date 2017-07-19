from model.player import Player


def test_player_equality():
    assert Player(id_=1, login='old_nick') == Player(id_=1, login='new_nick')


def test_player_indexing():
    p = Player(id_=1, login='x')
    assert {1: p}[1] == {p: p}[p]
