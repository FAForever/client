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


Running on Linux
-------
This guide is about runnning the client from source repository. For a [ready-made Arch-Linux package](https://aur.archlinux.org/cgit/aur.git/tree/PKGBUILD?h=python2-fafclient) [follow the instructions in the wiki](http://wiki.faforever.com/index.php?title=Setting_Up_FAF_Linux).

Clone this repository locally:

    git clone https://github.com/FAForever/client.git faf-client
    
Create a python virtualenv for installing its dependencies:

    virtualenv2 ./faf-client-venv --system-site-packages
    ./faf-client-venv/bin/pip install -r ./faf-client/requirements.txt

Now download the `uid` executable:

    wget https://github.com/FAForever/uid/releases/download/v2.1.0/uid -O ./faf-client/lib/uid
    chmod +x ./faf-client/lib/uid

Note that the `uid` smurf protection executable needs to run `xrandr`, `lspci`, `lsblk` and `uname` to gather unique system information.

Run the client:

    cd ./faf-client && ../faf-client-venv/bin/python src/__main__.py

For more information see [the wiki](http://wiki.faforever.com/index.php?title=Setting_Up_FAF_Linux).

Running unit tests
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
