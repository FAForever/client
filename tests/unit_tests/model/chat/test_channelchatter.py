import pytest

from model.chat.channelchatter import ChannelChatter


@pytest.fixture
def channel(mocker):
    return mocker.Mock(spec_set=["id_key"])


@pytest.fixture
def chatter(mocker):
    return mocker.Mock(spec_set=["id_key"])


def test_id_is_tuple_of_channel_chatter_ids(channel, chatter):
    channel.id_key = "channel"
    chatter.id_key = "chatter"

    cc = ChannelChatter(channel, chatter, "")
    assert cc.id_key == (channel.id_key, chatter.id_key)


def test_setting_elevation(channel, chatter, mocker):
    old_el = ""
    new_el = "~"

    def check_update(new, old):
        assert new.elevation == new_el
        assert old.elevation == old_el

    cc = ChannelChatter(channel, chatter, old_el)

    call = mocker.Mock()
    cc.updated.connect(call)
    cc.updated.connect(check_update)
    cc.set_elevation(new_el)

    assert call.called
