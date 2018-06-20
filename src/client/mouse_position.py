
__all__ = ("MousePosition",)


class MousePosition(object):
    """
    Instance holds mouse edge information.
    """
    PADDING = 8

    def __init__(self, parent):
        self.parent = parent
        self.on_left_edge = False
        self.on_right_edge = False
        self.on_top_edge = False
        self.on_bottom_edge = False
        self.cursor_shape_change = False
        self.warning_buttons = dict()  # TODO: remove, unused?
        self.on_edges = False  # TODO: remove, unused?

    def update_mouse_position(self, pos):
        self.on_left_edge = pos.x() < MousePosition.PADDING
        self.on_right_edge = pos.x() > self.parent.size().width() - MousePosition.PADDING
        self.on_top_edge = pos.y() < MousePosition.PADDING
        self.on_bottom_edge = pos.y() > self.parent.size().height() - MousePosition.PADDING

    def reset_to_false(self):
        self.on_left_edge = False
        self.on_right_edge = False
        self.on_top_edge = False
        self.on_bottom_edge = False
        self.cursor_shape_change = False

    @property
    def on_top_left_edge(self):
        return self.on_top_edge and self.on_left_edge

    @property
    def on_bottom_left_edge(self):
        return self.on_bottom_edge and self.on_left_edge

    @property
    def on_top_right_edge(self):
        return self.on_top_edge and self.on_right_edge

    @property
    def on_bottom_right_edge(self):
        return self.on_bottom_edge and self.on_right_edge

    def is_on_edge(self):
        return self.on_left_edge or self.on_right_edge or self.on_top_edge or self.on_bottom_edge
