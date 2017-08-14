from model.ircuser import IrcUser


def test_simple_init():
    IrcUser("Name", "Hostname")


def test_update_signal(mocker):
    p = IrcUser("Name", "Hostname")
    updated = mocker.Mock()

    def check_signal(new, old):
        assert old.hostname == "Hostname"
        assert new.hostname == "Newhost"

    p.updated.connect(updated)
    p.updated.connect(check_signal)
    p.update(hostname="Newhost")
    assert updated.called


def test_elevation_setting(mocker):
    p = IrcUser("Name", "Hostname")
    updated = mocker.Mock()

    def check_signal(new, old):
        assert "aeolus" not in old.elevation
        assert "aeolus" in new.elevation
        assert new.elevation["aeolus"] == "@"

    p.updated.connect(updated)
    p.updated.connect(check_signal)
    p.set_elevation("aeolus", "@")
    assert updated.called


def test_elevation_clearing(mocker):
    p = IrcUser("Name", "Hostname")
    p.set_elevation("aeolus", "@")

    updated = mocker.Mock()

    def check_signal(new, old):
        assert "aeolus" not in new.elevation
        assert "aeolus" in old.elevation
        assert old.elevation["aeolus"] == "@"

    p.updated.connect(updated)
    p.updated.connect(check_signal)
    p.set_elevation("aeolus", None)
    assert updated.called
