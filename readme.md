 

FA Forever - Lobby 
------------------
master|develop
 ------------ | -------------
[![Build Status](https://travis-ci.org/FAForever/lobby.svg?branch=master)](https://travis-ci.org/FAForever/lobby) | [![Build Status](https://travis-ci.org/FAForever/lobby.svg?branch=develop)](https://travis-ci.org/FAForever/lobby)
[![Coverage Status](https://coveralls.io/repos/FAForever/lobby/badge.png?branch=coverage)](https://coveralls.io/r/FAForever/lobby?branch=master) | [![Coverage Status](https://coveralls.io/repos/FAForever/lobby/badge.png?branch=coverage)](https://coveralls.io/r/FAForever/lobby?branch=develop)

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

Run the lobby from the main directory using:

    python2 src

Run the unit test suite using:

    python2 runtests.py

License
-------

GPLv3. See the [license](license.txt) file.
