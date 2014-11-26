from fa.init_file import InitFile

__author__ = 'Sheeo'

from flexmock import flexmock

process_mock = flexmock()
settings_mock = flexmock()

import fa
import fa.play

fa.play.instance = process_mock
fa.play.Settings = settings_mock


def test_launches_process_with_given_arguments(game_version, tmpdir):
    game_info = {
        'uid': 0,
        'recorder': 'Sheeo',
        'version': game_version
    }
    expected_args = [('some-arg', 'test')]

    def validate_args(game_info, args, detach, init_file):
        for k, v in expected_args:
            assert k in dict(args).keys()
            assert dict(args)[k] == v
        return True

    settings_mock.should_receive('get').with_args('WRITE_GAME_LOG', 'FA').and_return(False)
    settings_mock.should_receive('get').with_args('BIN', 'FA').and_return(str(tmpdir))
    process_mock.should_receive('run').replace_with(validate_args)
    assert fa.run(game_info, 0, expected_args)


def test_constructs_and_uses_init_file_from_game_version(game_version, tmpdir):
    game_info = {
        'uid': 0,
        'recorder': 'Sheeo',
        'version': game_version
    }
    settings_mock.should_receive('get').with_args('WRITE_GAME_LOG', 'FA').and_return(False)
    settings_mock.should_receive('get').with_args('BIN', 'FA').and_return(str(tmpdir))

    def validate_args(game_info, args, detach, init_file):
        assert dict(args)['init'] == str(tmpdir.join('init_%s.lua' % game_version.main_mod.name))
        return True
    process_mock.should_receive('run').replace_with(validate_args).once()
    assert fa.run(game_info, 0)
