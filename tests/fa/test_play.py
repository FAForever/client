__author__ = 'Sheeo'

from flexmock import flexmock

from config import Settings

process_mock = flexmock()
settings_mock = flexmock()

import fa
import fa.play

fa.play.instance = process_mock
fa.play.Settings = settings_mock


def test_constructs_and_uses_init_file_from_game_version(game_version, tmpdir):
    game_info = {
        'uid': 0,
        'recorder': 'Sheeo',
        'version': game_version
    }
    settings_mock.should_receive('get').with_args('WRITE_GAME_LOG', 'FA').and_return(False)
    settings_mock.should_receive('get').with_args('BIN', 'FA').and_return(str(tmpdir))
    settings_mock.should_receive('get').with_args('MODS_PATH', 'FA').and_return(str(tmpdir))

    def validate_args(game_info, args, detach, init_file):
        assert dict(args)['init'] == str(tmpdir.join('init_%s.lua' % game_version.main_mod.name))
        return True
    process_mock.should_receive('run').replace_with(validate_args).once()
    assert fa.run(game_info, 0)
