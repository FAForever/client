from fa import path
import os
import shutil

__author__ = 'Dragonfire'

root = 'forged_alliance'
root2 = 'supcom'

def test_set():
    CorrectFolder = root
    path.setGameFolderFA(CorrectFolder)

    assert path.getGameFolderFA() == CorrectFolder

def test_differentSet():
    folderFA = root
    folderSC = root2
    path.setGameFolderFA(folderFA)
    path.setGameFolderSC(folderSC)
    assert path.getGameFolderFA() == folderFA
    assert path.getGameFolderSC() == folderSC

def test_hotfixFA():
    folderFA = root

    # create fake game
    gamedata = os.path.join(root, 'gamedata')
    try:
        os.makedirs(gamedata)
    except os.error:
        pass
    lua = os.path.join(gamedata, 'lua.scd')
    open(lua, 'a').close()

    # positive test
    subfolders = ['\\bin',
                  '\\bin\\SupremeCommander.exe']
    for sub in subfolders:
        path.setGameFolderFA(folderFA + sub)
        assert path.getGameFolderFA() == folderFA

    # negative test
    subfolders = ['\\bin\\bin', '\\bin\\forgedalliance.exe', '\\bin\\supremecommander.exe']
    for sub in subfolders:

        tmpPath  = folderFA + sub
        path.setGameFolderFA(tmpPath)
        assert path.getGameFolderFA() == tmpPath

    # clean up gamedata
    shutil.rmtree(folderFA)