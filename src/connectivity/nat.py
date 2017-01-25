import time
from decorators import with_logger
import logging
from abc import ABCMeta, abstractmethod


UPNP_APP_NAME = "Forged Alliance Forever"

# find out what modules that are available
Services = list()
for m, c in [("natpmp", "NAT_PMP"), ("win32com.client", "UPnP_Win32")]:
    try:
        globals()[m] = __import__(m)
        Services.append(c)
    except ImportError:
        pass


class ServiceNotFound(Exception):
    pass


class AllocationError(Exception):
    pass


class NAT_Base(object):
    __metaclass__ = ABCMeta

    ip = None
    internal_port = None
    public_port = None
    protocol = None
    expire_at = None
    allocated = False

    def __init__(self, ip, port, protocol='UDP'):
        self.ip = ip
        self.internal_port = port
        self.public_port = port
        self.protocol = protocol

    @abstractmethod
    def _allocate(self):
        pass

    def allocate(self):
        if self.allocated:
            return

        self.allocated = self._allocate()
        return self.allocated

    @abstractmethod
    def _release(self):
        pass

    def release(self):
        if not self.allocated:
            return

        self.allocated = self._release()
        return self.allocated


@with_logger
class NAT_PMP(NAT_Base):

    def get_natpmp_protocol(self):
        p = self.protocol.upper()
        if p == 'UDP':
            return natpmp.NATPMP_PROTOCOL_UDP
        elif p == 'TCP':
            return natpmp.NATPMP_PROTOCOL_TCP

        return None

    def _allocate(self):
        try:
            gateway = natpmp.get_gateway_addr()
            if not gateway:
                raise ServiceNotFound

            proto = self.get_natpmp_protocol()
            pmp_result = natpmp.map_port(
                proto,
                self.internal_port,
                self.internal_port,
                4 * 60 * 60,
                gateway_ip=gateway,
                retry=1)
            self.public_port = pmp_result.public_port
            self.expire_at = time.time() + pmp_result.lifetime

            return True
        except natpmp.NATPMPUnsupportedError as e:
            raise ServiceNotFound

        return False

    def _release(self):
        proto = self.get_natpmp_protocol()
        gateway = natpmp.get_gateway_addr()
        natpmp.map_port(proto, self.internal_port, 0, 0, gateway_ip=gateway, retry=1)
        return True


@with_logger
class UPnP_Win32(NAT_Base):

    def get_mapping(self):
        import win32com
        return win32com.client.Dispatch("HNetCfg.NATUPnP").StaticPortMappingCollection

    def _allocate(self):
        mappingPorts = self.get_mapping()

        if not mappingPorts:
            self._logger.debug("Couldn't get StaticPortMappingCollection")
            raise ServiceNotFound

        mappingPorts.Add(self.internal_port, self.protocol, self.public_port, self.ip, True, UPNP_APP_NAME)

        return True

    def _release(self):
        mappingPorts = self.get_mapping()

        if not mappingPorts:
            self._logger.debug("Couldn't get StaticPortMappingCollection")
            return

        if mappingPorts.Count:
            for mappingPort in mappingPorts:
                if mappingPort.Description == UPNP_APP_NAME:
                    mappingPorts.Remove(mappingPort.ExternalPort, mappingPort.Protocol)
                    self._logger.debug("Released external %d port %s", mappingPort.ExternalPort, mappingPort.Protocol)
                else:
                    self._logger.debug("No mappings found / collection empty.")


@with_logger
class NAT_Service:
    service = None

    def allocate(self, ip, port, protocol="UDP"):
        success = False
        for name in Services:  # determined at start of script
            c = eval(name)(ip, port, protocol)

            try:
                self._logger.info("Trying to allocate %s:%d using %s", ip, port, name)
                c.allocate()
                self._logger.info("%d was successfully bound to %s:%d", c.internal_port, c.ip, c.public_port)
                self.service = c
                return True

            except ServiceNotFound as e:
                self._logger.debug("%s: No service found", name)
            except AllocationError as e:
                self._logger.error("Failed binding %s, port already in use?", port)

        return False

    def release(self):
        if not self.service:
            return

        self._logger.info("Removing UPnP port mappings.")
        self.service.release()
        del self


nat = NAT_Service()


def CreatePortMapping(ip, port, protocol='UDP'):
    nat.allocate(ip, port, protocol)


def RemovePortMapping():
    nat.release()
