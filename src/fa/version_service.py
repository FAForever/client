from PyQt4 import QtCore

from shared.api.service import Service
from shared.api import *


__author__ = 'Sheeo'


class VersionService(Service):
    def __init__(self, network_manager):
        Service.__init__(self, network_manager)

    def default_version_for(self, mod):
        return self._get(VERSION_SERVICE_URL + "/default/"+mod)

