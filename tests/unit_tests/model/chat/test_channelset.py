import pytest

from model.chat.channel import ChannelID, ChannelType
from model.chat.channelset import Channelset


class MockChannels():
    def __init__(self, mock):
        self._mock = mock

    def get(self, cid):
        mock_channel = self._mock.Mock(spec_set=["id_key", "is_base"])
        mock_channel.id_key = cid
        return mock_channel


@pytest.fixture
def channels(mocker):
    return MockChannels(mocker)


def test_adding_channel(channels, mocker):
    added = mocker.Mock()
    channelset = Channelset([])
    channelset.added.connect(added)

    cid = ChannelID(ChannelType.PUBLIC, "aeolus")
    new_channel = channels.get(cid)
    channelset[cid] = new_channel

    assert channelset[cid] is new_channel
    added.assert_called_with(new_channel)
    assert len(channelset) == 1
    assert [cid for cid in channelset] == [cid]


def test_removing_channel(channels, mocker):
    removed = mocker.Mock()
    channelset = Channelset([])
    channelset.removed.connect(removed)

    cid = ChannelID(ChannelType.PUBLIC, "aeolus")
    new_channel = channels.get(cid)
    channelset[cid] = new_channel
    assert not removed.called

    del channelset[cid]
    assert cid not in channelset
    removed.assert_called_with(new_channel)
    assert len(channelset) == 0
    assert [cid for cid in channelset] == []


def test_adding_mismatched_cid_is_value_error(channels):
    channelset = Channelset([])
    cid = ChannelID(ChannelType.PUBLIC, "aeolus")
    cid2 = ChannelID(ChannelType.PUBLIC, "odysseus")
    cid3 = ChannelID(ChannelType.PRIVATE, "aeolus")
    new_channel = channels.get(cid)

    with pytest.raises(ValueError):
        channelset[cid2] = new_channel
    with pytest.raises(ValueError):
        channelset[cid3] = new_channel


def test_adding_same_cid_twice_is_value_error(channels):
    channelset = Channelset([])
    cid1 = ChannelID(ChannelType.PUBLIC, "aeolus")
    cid2 = ChannelID(ChannelType.PUBLIC, "aeolus")
    new_channel1 = channels.get(cid1)
    new_channel2 = channels.get(cid2)

    channelset[cid1] = new_channel1
    with pytest.raises(ValueError):
        channelset[cid2] = new_channel2
