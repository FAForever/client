from model.player import Player

DEFAULT_DICT = {
    "id_": 17,
    "login": "TesterNoob",
    "global_rating": (1455, 160),
    "ladder_rating": (1192, 216),
    "number_of_games": 374,
    "avatar": {
        'url': 'http://content.faforever.com/faf/avatars/GW_Cybran.png',
        'tooltip': 'Liberate !',
    },
    "country": "PL",
}

NONOPTIONAL_DICT = {
    "id_": 17,
    "login": "TesterNoob",
}


def test_simple_init():
    Player(**DEFAULT_DICT)


def test_required_args_only():
    Player(**NONOPTIONAL_DICT)


def test_update_signal(mocker):
    p = Player(**DEFAULT_DICT)
    updated = mocker.Mock()

    def check_signal(new, old):
        assert old.number_of_games == 374
        assert new.number_of_games == 375

    p.updated.connect(updated)
    p.updated.connect(check_signal)
    p.update(number_of_games=375)
    assert updated.called


def test_immutable_id_login():
    p = Player(**DEFAULT_DICT)
    p.update(id_=18, login="Malicious")
    assert p.id == 17
    assert p.login == "TesterNoob"


def test_player_equality():
    assert Player(id_=1, login='old_nick') == Player(id_=1, login='new_nick')


def test_player_indexing():
    p = Player(id_=1, login='x')
    assert {1: p}[1] == {p: p}[p]
