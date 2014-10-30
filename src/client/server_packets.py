from PyQt4 import QtCore

class ServerPackets(QtCore.QObject):

    # signals for incoming network packages
    statsInfo = QtCore.pyqtSignal(dict)  # deprecated?
    tutorialsInfo = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=tutorials_info
    modInfo = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=mod_info
    gameInfo = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=game_info
    modVaultInfo = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=modvault_info
    coopInfo = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=coop_info
    featuredModManagerInfo = QtCore.pyqtSignal(dict) #https://github.com/FAForever/server/search?q=mod_manager_info
    replayVault = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=replay_vault
    coopLeaderBoard = QtCore.pyqtSignal(dict)  # deprecated
    ladderMapsList = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=ladder_maps

    # for team management
    teamInfo = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=team_info
    teamInvitation = QtCore.pyqtSignal(dict)  # FaServerThread.py, gwserver\lobby.py

    # unused
    newGame = QtCore.pyqtSignal(str)
    tourneyInfo = QtCore.pyqtSignal(dict)  # https://github.com/FAForever/server/search?q=tournament_info
    tourneyTypesInfo = QtCore.pyqtSignal(dict)  # deprecated

    # no signal found
    welcome = QtCore.pyqtSignal(dict)
    game_launch = QtCore.pyqtSignal(dict)
    modvault_list_info = QtCore.pyqtSignal(dict)
    matchmaker_info = QtCore.pyqtSignal(dict)
    avatar = QtCore.pyqtSignal(dict)
    admin = QtCore.pyqtSignal(dict)
    social = QtCore.pyqtSignal(dict)

    translation_table = {'stats' : 'statsInfo',
                         'tournament_types_info' : 'tourneyTypesInfo',
                         'tutorials_info' : 'tutorialsInfo',
                         'tournament_info' : 'tourneyInfo',
                         'mod_info' : 'modInfo',
                         'game_info' : 'gameInfo',
                         'modvault_info' : 'modVaultInfo',
                         'coop_info' : 'coopInfo',
                         'mod_manager_info' : 'featuredModManagerInfo',
                         'replay_vault' : 'replayVault',
                         'coop_leaderboard' : 'coopLeaderBoard',
                         'ladder_maps' : 'ladderMapsList',
                         'team_info' : 'teamInfo',
                         'team' : 'teamInvitation'}

    def translate(self, command):
        if command in self.translation_table:
            return self.translation_table[command]
        raise Exception('no translation', command)
