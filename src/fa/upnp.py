#-------------------------------------------------------------------------------
# Copyright (c) 2012 Gael Honorez.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#-------------------------------------------------------------------------------





'''
Created on Mar 22, 2012

@author: thygrrr
'''
import logging
import sys
import util
logger = logging.getLogger(__name__)


UPNP_APP_NAME = "Forged Alliance Forever"

# Fields in mappingPort
# UpnpPort.Description
# UpnpPort.ExternalPort
# UpnpPort.ExternalIPAddress
# UpnpPort.InternalClient
# UpnpPort.InternalPort
# UpnpPort.Protocol
# UpnpPort.Enabled

def dumpMapping(mappingPort):
    logger.info("-> %s mapping of %s:%d to %s:%d" % (mappingPort.Protocol, mappingPort.InternalClient, mappingPort.InternalPort, mappingPort.ExternalIPAddress, mappingPort.ExternalPort))


def createPortMapping(ip, port, protocol = "UDP"):
    logger.info("Creating UPnP port mappings...")
    try:
        import win32com.client
        NATUPnP = win32com.client.Dispatch("HNetCfg.NATUPnP")
        mappingPorts = NATUPnP.StaticPortMappingCollection

        if mappingPorts:
            mappingPorts.Add(port, protocol, port, ip, True, UPNP_APP_NAME)
            for mappingPort in mappingPorts:
                if mappingPort.Description == UPNP_APP_NAME:
                    dumpMapping(mappingPort)
        else:
            logger.error("Couldn't get StaticPortMappingCollection")
    except:
        logger.error("Exception in UPnP createPortMapping.", exc_info = sys.exc_info())
        util.CrashDialog(sys.exc_info()).exec_()




def removePortMappings():
    logger.info("Removing UPnP port mappings...")
    try:
        import win32com.client
        NATUPnP = win32com.client.Dispatch("HNetCfg.NATUPnP")
        mappingPorts = NATUPnP.StaticPortMappingCollection

        if mappingPorts:
            if mappingPorts.Count:
                for mappingPort in mappingPorts:
                    if mappingPort.Description == UPNP_APP_NAME:
                        dumpMapping(mappingPort)
                        mappingPorts.Remove(mappingPort.ExternalPort, mappingPort.Protocol)
            else:
                logger.info("No mappings found / collection empty.")
        else:
            logger.error("Couldn't get StaticPortMappingCollection")
    except:
        logger.error("Exception in UPnP removePortMappings.", exc_info = sys.exc_info())
        util.CrashDialog(sys.exc_info()).exec_()
