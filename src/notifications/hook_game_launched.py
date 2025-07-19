import src.notifications as ns
from src.notifications.ns_hook import NsHook


class NsHookGameLaunchedCustom(NsHook):
    def __init__(self):
        super().__init__(ns.Notifications.CUSTOM_GAME_LAUNCHED)
        self.ingame = True


class NsHookGameLaunchedLadder(NsHook):
    def __init__(self):
        super().__init__(ns.Notifications.LADDER_GAME_LAUNCHED)
        self.ingame = True
