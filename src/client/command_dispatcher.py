from PyQt4 import QtCore


class CommandDispatcher(QtCore.QObject):
    # Signals for incoming network packages
    tutorialsInfo = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=tutorials_info
    modInfo = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=mod_info
    gameInfo = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=game_info
    modVaultInfo = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=modvault_info
    coopInfo = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=coop_info
    replayVault = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=replay_vault

    _signals = {
        'tutorials_info': 'tutorialsInfo',
        'mod_info': 'modInfo',
        'game_info': 'gameInfo',
        'modvault_info': 'modVaultInfo',
        'coop_info': 'coopInfo',
        'replay_vault': 'replayVault'
    }

    def dispatch(self, command, args):
        if command in self._signals:
            getattr(self, self._signals[command]).emit(args)
            return True
