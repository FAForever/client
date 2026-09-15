def test_request_failure_discards_access_token(application):
    from PyQt6.QtNetworkAuth import QAbstractOAuth

    from src.oauth.oauth_flow import OAuth2Flow

    flow = OAuth2Flow()
    flow.setToken("expired-token")

    flow.requestFailed.emit(QAbstractOAuth.Error.NetworkError)

    assert flow.token() == ""
