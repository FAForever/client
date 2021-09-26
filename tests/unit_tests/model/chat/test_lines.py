import pytest

from model.chat.channel import Lines


def test_lines_dont_care_about_line_internals():
    o = object()

    for item in [1, "a", o]:
        lines = Lines()
        lines.add_line(item)
        assert [i for i in lines] == [item]


def test_lines_add_latest_last():
    lines = Lines()
    for item in range(5):
        lines.add_line(item)

    assert [i for i in lines] == list(range(5))


def test_lines_emit_add_remove_signals(mocker):
    lines = Lines()
    added = mocker.Mock()
    removed = mocker.Mock()
    lines.added.connect(added)
    lines.removed.connect(removed)

    lines.add_line("a")
    assert added.called
    assert not removed.called
    added.reset_mock()

    lines.remove_lines(1)
    removed.assert_called_with(1)
    assert not added.called


def test_lines_remove_acts_like_queue():
    lines = Lines()
    for item in range(5):
        lines.add_line(item)

    lines.remove_lines(2)
    assert [i for i in lines] == [2, 3, 4]


def test_lines_len():
    lines = Lines()
    for item in range(5):
        lines.add_line(item)
    lines.remove_lines(2)
    assert len(lines) == 3


def test_remove_more_lines_than_len_removes_len_lines(mocker):
    lines = Lines()
    removed = mocker.Mock()
    lines.removed.connect(removed)

    for item in range(5):
        lines.add_line(item)

    lines.remove_lines(15)
    removed.assert_called_with(5)
    assert len(lines) == 0
    assert [i for i in lines] == []


def test_lines_zero_remove_does_nothing(mocker):
    lines = Lines()
    removed = mocker.Mock()
    lines.removed.connect(removed)

    for item in range(5):
        lines.add_line(item)

    lines.remove_lines(0)
    assert not removed.called
    assert [i for i in lines] == list(range(5))


def test_remove_on_empty_list_does_nothing(mocker):
    lines = Lines()
    removed = mocker.Mock()
    lines.removed.connect(removed)

    lines.remove_lines(15)
    assert not removed.called
    assert [i for i in lines] == []


def test_negative_remove_number_is_value_error():
    lines = Lines()
    with pytest.raises(ValueError):
        lines.remove_lines(-5)
