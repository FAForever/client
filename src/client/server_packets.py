from PyQt4 import QtCore

class ServerPackets(QtCore.QObject):

    # signals for incoming network packages
    tutorialsInfo = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=tutorials_info
    modInfo = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=mod_info
    gameInfo = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=game_info
    modVaultInfo = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=modvault_info
    coopInfo = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=coop_info
    replayVault = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=replay_vault

    translation_table = {'tutorials_info' : 'tutorialsInfo',
                         'mod_info' : 'modInfo',
                         'game_info' : 'gameInfo',
                         'modvault_info' : 'modVaultInfo',
                         'coop_info' : 'coopInfo',
                         'replay_vault' : 'replayVault'}

    def translate(self, command):
        if command in self.translation_table:
            return getattr(self, self.translation_table[command])
        return None
