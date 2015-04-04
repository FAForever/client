# FA Forever - Lobby

This is the source code for the [Forged Alliance Forever](http://www.faforever.com/) lobby.

master|develop
 ------------ | -------------
[![Build Status](https://travis-ci.org/FAForever/lobby.svg?branch=master)](https://travis-ci.org/FAForever/lobby) | [![Build Status](https://travis-ci.org/FAForever/lobby.svg?branch=develop)](https://travis-ci.org/FAForever/lobby)
[![Coverage Status](https://coveralls.io/repos/FAForever/lobby/badge.png?branch=coverage)](https://coveralls.io/r/FAForever/lobby?branch=master) | [![Coverage Status](https://coveralls.io/repos/FAForever/lobby/badge.png?branch=coverage)](https://coveralls.io/r/FAForever/lobby?branch=develop)
[![Scrutinizer Code Quality](https://scrutinizer-ci.com/g/FAForever/client/badges/quality-score.png?b=master)](https://scrutinizer-ci.com/g/FAForever/client/?branch=master) | [![Scrutinizer Code Quality](https://scrutinizer-ci.com/g/FAForever/client/badges/quality-score.png?b=develop)](https://scrutinizer-ci.com/g/FAForever/client/?branch=develop)



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
