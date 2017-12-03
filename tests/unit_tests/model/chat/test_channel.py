import pytest
from model.chat.channel import Channel, ChannelID, ChannelType


@pytest.fixture
def lines(mocker):
    return mocker.Mock(spec_set=[])


def test_setting_topic(lines, mocker):
    old_topic = ""
    new_topic = "The gloves are comming off."

    def check_update(new, old):
        assert new.topic == new_topic
        assert old.topic == old_topic

    cid = ChannelID(ChannelType.PUBLIC, "aeolus")
    channel = Channel(cid, lines, old_topic)
    topic_call = mocker.Mock()
    channel.updated.connect(topic_call)
    channel.updated.connect(check_update)
    channel.set_topic(new_topic)
