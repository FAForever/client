import pytest
from util.gameurl import GameUrl, GameUrlType

# NOTE - any time url format gets updated, fix below URLs to be correct
# in everything except what we test for!
# Since people can post any URL in chat they please, we need to test explicit
# url format.
# Example live replay URL:
# 'faflive://lobby.faforever.com/9876?map=Sedongs&mod=coop&uid=123456'
# Example open game URL:
# 'fafgame://lobby.faforever.com/342423/3453.SCFAreplay?map=Sedongs&mod=faf'


def test_example_format_passes():
    live_url = (
        'faflive://lobby.faforever.com/342423/3453.SCFAreplay?map=Canis River'
        '&mod=faf'
    )
    open_url = (
        'fafgame://lobby.faforever.com/9876?map=Sedongs&mod=coop&uid=123456'
    )

    gurl = GameUrl.from_url(live_url)
    assert gurl.game_type == GameUrlType.LIVE_REPLAY
    assert gurl.map == "Canis River"
    assert gurl.mod == "faf"
    assert gurl.uid == 342423
    assert gurl.player == "3453"
    assert gurl.mods is None

    gurl = GameUrl.from_url(open_url)
    assert gurl.game_type == GameUrlType.OPEN_GAME
    assert gurl.map == "Sedongs"
    assert gurl.mod == "coop"
    assert gurl.uid == 123456
    assert gurl.player == "9876"
    assert gurl.mods is None


def test_to_url_and_back_works():
    def test_values(gtype, map_, mod, uid, pid, mods):
        gurl = GameUrl(gtype, map_, mod, uid, pid, mods)
        url = gurl.to_url()
        print(url)
        gurl2 = GameUrl.from_url(url)
        assert gurl2.game_type == gtype
        assert gurl2.map == map_
        assert gurl2.mod == mod
        assert gurl2.uid == uid
        assert gurl2.player == pid
    test_values(
        GameUrlType.LIVE_REPLAY,
        "Canis River",
        "faf",
        342423,
        "3453",
        "[]",
    )
    test_values(
        GameUrlType.OPEN_GAME,
        "Sedongs",
        "coop",
        123456,
        "Wesmania",
        "[]",
    )


def test_playername_accepts_both_uid_and_name():
    live_url = (
        'faflive://lobby.faforever.com/342423/Wesmania.SCFAreplay?map=Canis '
        'River&mod=faf'
    )
    live_url2 = (
        'faflive://lobby.faforever.com/342423/12346.SCFAreplay?map=Canis '
        'River&mod=faf'
    )
    open_url = (
        'fafgame://lobby.faforever.com/Wesmania?map=Sedongs&mod=coop'
        '&uid=123456'
    )
    open_url2 = (
        'fafgame://lobby.faforever.com/123456?map=Sedongs&mod=coop&uid=123456'
    )
    for u in [live_url, live_url2, open_url, open_url2]:
        GameUrl.from_url(u)


def test_mods_parameter_is_optional():
    live_url = (
        'faflive://lobby.faforever.com/342423/3453.SCFAreplay?map=Canis River'
        '&mod=faf'
    )
    gurl = GameUrl.from_url(live_url)
    assert gurl.mods is None

    live_url = (
        'faflive://lobby.faforever.com/342423/3453.SCFAreplay?map=Canis River'
        '&mod=faf&mods=[]'
    )
    gurl = GameUrl.from_url(live_url)
    assert gurl.mods == '[]'


def test_invalid_scheme_throws_value_error():
    live_url = (
        'http://lobby.faforever.com/342423/3453.SCFAreplay?map=Canis River'
        '&mod=faf'
    )
    open_url = (
        'https://lobby.faforever.com/9876?map=Sedongs&mod=coop&uid=123456'
    )
    for u in [live_url, open_url]:
        with pytest.raises(ValueError):
            GameUrl.from_url(u)


def test_missing_map_throws_value_error():
    live_url = 'faflive://lobby.faforever.com/342423/3453.SCFAreplay?mod=faf'
    open_url = 'fafgame://lobby.faforever.com/9876?mod=coop&uid=123456'
    for u in [live_url, open_url]:
        with pytest.raises(ValueError):
            GameUrl.from_url(u)


def test_missing_mod_throws_value_error():
    live_url = (
        'faflive://lobby.faforever.com/342423/3453.SCFAreplay'
        '?map=Canis River'
    )
    open_url = 'fafgame://lobby.faforever.com/9876?map=Sedongs&uid=123456'
    for u in [live_url, open_url]:
        with pytest.raises(ValueError):
            GameUrl.from_url(u)


def test_missing_uid_throws_value_error():
    live_url = (
        'faflive://lobby.faforever.com/3453.SCFAreplay?map=Canis River&mod=faf'
    )
    open_url = 'fafgame://lobby.faforever.com/9876?map=Sedongs&mod=coop'
    for u in [live_url, open_url]:
        with pytest.raises(ValueError):
            GameUrl.from_url(u)


def test_bad_replay_suffix_throws_value_error():
    live_url = (
        'faflive://lobby.faforever.com/342423/3453.blahblah?map=Canis River'
        '&mod=faf'
    )
    with pytest.raises(ValueError):
        GameUrl.from_url(live_url)


def test_too_short_path_throws_value_error():
    live_url = (
        'faflive://lobby.faforever.com/3453.SCFAreplay?map=Canis River&mod=faf'
    )
    open_url = 'fafgame://lobby.faforever.com?map=Sedongs&mod=coop&uid=123456'
    for u in [live_url, open_url]:
        with pytest.raises(ValueError):
            GameUrl.from_url(u)


def test_malformed_url_throws_value_error():
    for u in ["This is not a URL at all", 42, None]:
        with pytest.raises(ValueError):
            GameUrl.from_url(u)


def test_schema_determines_if_url_is_game():
    game1 = 'faflive://'
    game2 = 'fafgame://'
    notgame = 'http://'

    for u in [game1, game2]:
        assert GameUrl.is_game_url(u)
    assert not GameUrl.is_game_url(notgame)
