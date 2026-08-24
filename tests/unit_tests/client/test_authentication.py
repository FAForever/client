from unittest.mock import call


def test_login_failure_allows_fresh_connection(application, client_instance, mocker):
    from src.client.clientstate import ClientState
    from src.util.gameurl import GameUrl

    disconnect = mocker.patch.object(client_instance, "disconnect_")
    show_login_widget = mocker.patch.object(client_instance, "show_login_widget")
    mocker.patch.object(client_instance, "_state", ClientState.LOGGED_IN)
    mocker.patch.object(client_instance, "_auto_relogin", True)
    lifecycle = mocker.Mock()
    lifecycle.attach_mock(disconnect, "disconnect")
    lifecycle.attach_mock(show_login_widget, "show_login_widget")

    client_instance.on_login_attempt_failed()

    assert client_instance.state == ClientState.DISCONNECTED
    assert not client_instance._auto_relogin
    assert lifecycle.mock_calls == [call.disconnect(), call.show_login_widget()]

    mocker.patch.object(client_instance.replayServer, "doListen", return_value=True)
    mocker.patch.object(client_instance.replayServer, "serverPort", return_value=12345)
    connect = mocker.patch.object(client_instance.lobby_connection, "do_connect")
    mocker.patch.object(GameUrl, "PORT", -1)

    assert client_instance.do_connect()
    connect.assert_called_once_with()
