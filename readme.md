 

FA Forever - Lobby 
------------------
master|develop
 ------------ | -------------
[![Build Status](https://travis-ci.org/FAForever/lobby.svg?branch=master)](https://travis-ci.org/FAForever/lobby) | [![Build Status](https://travis-ci.org/FAForever/lobby.svg?branch=develop)](https://travis-ci.org/FAForever/lobby)
 

This is the source code for the FA Forever Lobby.

Pre-requisites are:

- Python 2.7.x
- PyQt4 4.7+
- Requirements as in the [requirements](requirements.txt) file.

    pip install -r requirements.txt

If you have some trouble with installing:

- **cx\_Freeze**: [Can't compile cx_Freeze in Ubuntu 13.04](https://bitbucket.org/anthony_tuininga/cx_freeze/issue/32/cant-compile-cx_freeze-in-ubuntu-1304)
- **pygit2**: manual compile
- **lupa**: sudo apt-get install lua5.1-dev
- May recompile /src/mumbleconnector/mumble_link.so for your system [mumbleconnector](https://github.com/hacst/mumble_link)

If you want to contribute back to the project, please make a fork and create
pull-requests of your changes.

- **NEW** Pull Requests must have py.test unit test coverage


Running
-------

Run the lobby from the main directory using:

    python2 src

Run the unit test suite using:

    python2 runtests.py

License
-------

GPLv3. See the [license](license.txt) file.
