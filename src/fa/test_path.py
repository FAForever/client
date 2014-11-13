import path


__author__ = 'Dragonfire'


def test_set():
    CorrectFolder = 'D:\Program Files (x86)\Steam\SteamApps\common\Supreme Commander Forged Alliance2'
    path.setGameFolderFA(CorrectFolder)

    assert path.getGameFolderFA() == CorrectFolder

def test_differentSet():
    folderFA = 'D:\Program Files (x86)\Steam\SteamApps\common\Supreme Commander Forged Alliance'
    folderSC = 'D:\Program Files (x86)\Steam\SteamApps\common\Supreme Commander'
    path.setGameFolderFA(folderFA)
    path.setGameFolderSC(folderSC)
    assert path.getGameFolderFA() == folderFA
    assert path.getGameFolderSC() == folderSC

def test_hotfixFA():
    folderFA = 'D:\Program Files (x86)\Steam\SteamApps\common\Supreme Commander Forged Alliance'

    # positive test
    subfolders = ['\\bin', '\\\\bin', '\\bin\\', '/bin', '/bin/', '\\bin\\SupremeCommander.exe', \
                  '\\\\bin\\\\SupremeCommander.exe', '/bin/SupremeCommander.exe']
    for sub in subfolders:
        path.setGameFolderFA(folderFA + sub)
        assert path.getGameFolderFA() == folderFA

    # negative test
    subfolders = ['\\bin\\bin', '\\bin\\forgedalliance.exe', '\\bin\\supremecommander.exe']
    for sub in subfolders:

        tmpPath  = folderFA + sub
        path.setGameFolderFA(tmpPath)
        assert path.getGameFolderFA() == tmpPath