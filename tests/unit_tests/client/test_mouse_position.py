import pytest

from PyQt5.QtCore import QPoint


@pytest.mark.parametrize("x,y", [(0, 0)])
def test_mouse_position(mouse_position, x: int, y: int):
    point = QPoint()
    point.setX(x)
    point.setY(y)

    assert not mouse_position.on_left_edge
    assert not mouse_position.on_right_edge
    assert not mouse_position.on_top_edge
    assert not mouse_position.on_bottom_edge
    assert not mouse_position.on_top_left_edge
    assert not mouse_position.on_bottom_left_edge
    assert not mouse_position.on_top_right_edge
    assert not mouse_position.on_bottom_right_edge
    assert not mouse_position.is_on_edge()

    mouse_position.update_mouse_position(point)
    assert mouse_position.on_left_edge
    assert not mouse_position.on_right_edge
    assert mouse_position.on_top_edge
    assert not mouse_position.on_bottom_edge
    assert mouse_position.on_top_left_edge
    assert not mouse_position.on_bottom_left_edge
    assert not mouse_position.on_top_right_edge
    assert not mouse_position.on_bottom_right_edge
    assert mouse_position.is_on_edge()

    mouse_position.reset_to_false()

    assert not mouse_position.on_left_edge
    assert not mouse_position.on_right_edge
    assert not mouse_position.on_top_edge
    assert not mouse_position.on_bottom_edge
    assert not mouse_position.on_top_left_edge
    assert not mouse_position.on_bottom_left_edge
    assert not mouse_position.on_top_right_edge
    assert not mouse_position.on_bottom_right_edge
    assert not mouse_position.is_on_edge()
