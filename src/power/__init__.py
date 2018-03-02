from power.actions import PowerActions
from power.view import PowerView


class PowerTools:
    def __init__(self, actions, view):
        self.power = 0
        self.actions = actions
        self.view = view

    @classmethod
    def build(cls, **kwargs):
        actions = PowerActions.build(**kwargs)
        view = PowerView.build(mod_actions=actions, **kwargs)
        return cls(actions, view)
