import pytest

import config


def test_client_sends_current_version(qtbot, mocker):
    import client
    c = client.instance
    mocker.patch('util.uniqueID', side_effect='some_unique_id')
    mocker.patch.object(c, 'send')

    c.perform_login()

    args, kwargs = c.send.call_args
    assert args[0]['version'] == config.VERSION


@pytest.mark.skipif(True, reason="Run this manually to test client update downloading")
def test_client_updater(qtbot):
    from client.updater import ClientUpdater

    updater = ClientUpdater("http://content.faforever.com/FAForever-0.10.125.msi")
    updater.exec_()
    qtbot.stop()
