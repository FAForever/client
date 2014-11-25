
import fa.version_service
from fa.version_service import VersionService

from flexmock import flexmock
from faftools.api.irestservice import IRESTService

__author__ = 'Sheeo'

network_manager = flexmock()
signal_mock = flexmock(connect=lambda func: True)
restmock = flexmock(IRESTService)
rest_response_mock = flexmock(done=signal_mock, error=signal_mock)


def test_returns_default_versions_for_mod():
    version_service = VersionService(network_manager)
    restmock.should_receive('_get').with_args(fa.version_service.VERSION_SERVICE_URL + "/default/faf") \
        .and_return(rest_response_mock()).once()
    version_service.versions_for('faf')
