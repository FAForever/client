from faftools.api.irestservice import IRESTService
from faftools.api import *

__author__ = 'Sheeo'

import logging
logger = logging.getLogger(__name__)


class VersionService(IRESTService):
    """
    Service to get available versions for mods, maps etc.

    TODO:
        - Use for setting the version of a hosted game,
          potentially within GameService
    """
    def __init__(self, network_manager):
        super(VersionService, self).__init__(network_manager)

    def versions_for(self, mod):
        """
        Get available versions for the given mod.

        :param mod: identifier for the mod, eg 'faf', 'blackops'
        :return: List of versions available of the mod
        """
        url = VERSION_SERVICE_URL + "/default/"+mod
        logger.debug("Getting default versions from: " + url)
        return self._get(url)

