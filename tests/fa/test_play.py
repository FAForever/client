__author__ = 'Sheeo'

from flexmock import flexmock

process_mock = flexmock()

import fa
import fa.play

fa.play.instance = process_mock


def test_launches_process_with_given_arguments():
    game_info = {
        'uid': 0,
        'recorder': 'Sheeo'
    }
    args = ['/some-arg', 'test']
    process_mock.should_receive('run').with_args(game_info, args).and_return(True).once()
    assert fa.run(game_info, 0, args)

