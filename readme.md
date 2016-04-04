FA Forever Client
=================

[![Stories in Ready](https://badge.waffle.io/faforever/client.png?label=ready&title=Ready)](http://waffle.io/faforever/client)

------------------
master|develop
 ------------ | -------------
[![Build Status](https://travis-ci.org/FAForever/client.svg?branch=master)](https://travis-ci.org/FAForever/client) [![Appveyor Status](https://ci.appveyor.com/api/projects/status/p15sk71sp957ij72/branch/master?svg=true)](https://ci.appveyor.com/project/Sheeo/client) | [![Build Status](https://travis-ci.org/FAForever/client.svg?branch=develop)](https://travis-ci.org/FAForever/client) [![Appveyor Status](https://ci.appveyor.com/api/projects/status/p15sk71sp957ij72/branch/develop?svg=true)](https://ci.appveyor.com/project/Sheeo/client)
[![Coverage Status](https://img.shields.io/coveralls/FAForever/client.svg?branch=master)](https://coveralls.io/r/FAForever/client) | [![Coverage Status](https://img.shields.io/coveralls/FAForever/client.svg?branch=develop)](https://coveralls.io/r/FAForever/client)
 

This is the source code for the FA Forever Lobby.

Pre-requisites are:

- Python 2.7.x
- PyQt4 4.7+
- Requirements as in the [requirements](requirements.txt) file.


    pip install -r requirements.txt


If you want to contribute back to the project, please make a fork and create
pull-requests of your changes.

Pull Requests must have py.test unit test coverage.


Running
-------
Before running unit tests, set PYTEST_QT_API as follows:

    export PYTEST_QT_API='pyqt4v2'

Run the lobby from the main directory using:

    python2 src

Run the unit test suite using:

    python2 runtests.py

License
-------

GPLv3. See the [license](license.txt) file.
