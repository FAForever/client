__author__ = 'Sheeo'

import os
import pytest

from fa.game_version import GameVersion
from fa.mod import Mod
from git import Version

from config import Settings


FAF_PATH = os.path.join(Settings.get('MODS_PATH', 'FA'), 'faf')

@pytest.fixture(scope='function')
def game_version():
    return GameVersion(Version('binary-patch', 'master', None, 'a41659780460fd8829fce87b479beaa8ac78e474'),
                       Mod('Forged Alliance Forever', 'faf', Version('faf', '3634', None, 'ed052486a19f7adc1adb3f65451af1a7081d2339')),
                       [],
                       '')
