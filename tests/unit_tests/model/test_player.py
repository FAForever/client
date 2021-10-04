from model.player import Player
from model.rating import RatingType

DEFAULT_DICT = {
    "id_": 17,
    "login": "TesterNoob",
    "ratings": {
        "global": {
            "rating": (1455, 160),
            "number_of_games": 374,
        },
        "ladder_1v1": {
            "rating": (1192, 216),
            "number_of_games": 374,
        },
        "tmm_2v2": {
            "rating": (888, 88),
            "number_of_games": 88,
        },
    },
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
        assert old.global_estimate == (1455 - 3 * 160)
        assert new.global_estimate == (1456 - 3 * 140)
        assert old.game_count() == 374
        assert new.game_count() == 375
        assert old.number_of_games == 374 + 374 + 88
        assert new.number_of_games == 375 + 374 + 88
        assert old.ladder_estimate == (1192 - 3 * 216)
        assert new.ladder_estimate == (1192 - 3 * 216)

    p.updated.connect(updated)
    p.updated.connect(check_signal)
    p.update(
        ratings={
            "global": {
                "rating": (1456, 140),
                "number_of_games": 375,
            },
            "ladder_1v1": {
                "rating": (1192, 216),
                "number_of_games": 374,
            },
            "tmm_2v2": {
                "rating": (888, 88),
                "number_of_games": 88,
            },
        },
    )
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


def test_player_repr():
    p = Player(**DEFAULT_DICT)
    assert str(p) == (
        "Player(id=17, login=TesterNoob, global_rating=(1455, 160), "
        "ladder_rating=(1192, 216))"
    )


def test_player_fields():
    p = Player(**DEFAULT_DICT)
    assert p.login == "TesterNoob"
    assert p.id == 17
    assert p.ratings is not None
    assert isinstance(p.ratings, dict) is True
    assert p.country == "PL"
    assert p.clan is None
    assert p.league is None
    assert p.avatar == {
        'url': 'http://content.faforever.com/faf/avatars/GW_Cybran.png',
        'tooltip': 'Liberate !',
    }


def test_missing_ratings():
    p = Player(**DEFAULT_DICT)
    p.update(ratings={})
    assert p.number_of_games == 0
    assert p.ladder_estimate == 0
    assert p.global_estimate == 0
    for rating_type in list(RatingType):
        assert p.rating_mean(rating_type.value) == 1500
        assert p.rating_deviation(rating_type.value) == 500
        assert p.rating_estimate(rating_type.value) == 0
        assert p.game_count(rating_type.value) == 0


def test_missing_number_of_games():
    p = Player(**DEFAULT_DICT)
    p.update(ratings={"global": {"rating": (1500, 500)}})
    assert p.number_of_games == 0
