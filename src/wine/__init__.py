#-------------------------------------------------------------------------------
# Copyright (c) 2015 Igor Kotrasinski.
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


import ctypes
import os

try:
    version = ctypes.windll.ntdll.wine_get_version()
except AttributeError:
    version = None

if version is not None:
    if os.getenv('WINEPREFIX', "") != "":
        prefix = os.environ['WINEPREFIX']
    else:    # Default ; we need to guess home directory
        prefix = '/home/' + os.environ['USERNAME'] + '/.wine'

    FAFpath = os.getcwd().replace('\\', '/');
    FAFpath = FAFpath[0].lower() + FAFpath[1:]  # wine uses lowercase
    FAFpath = prefix + '/dosdevices/' + FAFpath
