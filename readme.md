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

- Python 3.4+
- PyQt5 >=5.8
- Requirements as in the [requirements](requirements.txt) file.


    pip install -r requirements.txt


Contributing
-------

By contributing, you agree to license your work to the FAForever project in such a way that it can forever be distributed under the conditions of the GPL v3.0 license.

### Code-Style

[Downlord's FAF Client Contribution Guidelines](https://github.com/FAForever/java-guidelines/wiki/Contribution-Guidelines)
* [Quality has highest priority](https://github.com/FAForever/java-guidelines/wiki/Contribution-Guidelines#quality-has-highest-priority)
* [Write readable code](https://github.com/FAForever/java-guidelines/wiki/Contribution-Guidelines#write-readable-code)
* [Use comments only when absolutely necessary to explain complex algorithms or inherently unintuitive reasons for how or why your code functions](https://github.com/FAForever/java-guidelines/wiki/Contribution-Guidelines#avoid-javadoc-and-comments)
* [Use the logger](https://github.com/FAForever/java-guidelines/wiki/Contribution-Guidelines#logging)

### Issues, PRs, and commit formatting

1. Open an issue for every improvement or problem you want to work on
2. Open a PR that references the issue, name of the feature branch for the PR should start with issue number
3. Use reasonably structured commits in your PR, for example like this:
    1. Cosmetic changes necessary to prepare your work
    2. Infrastructure / low level changes necessary for your high-level feature/fix
    3. Implementation of your feature/fix
    4. Additional work, such as localizations
3. Use "Closes #xxx" in commit messages
4. Changelog messages of the form `* Fix the foo #issue (@myname #pr)` are appreciated when done in a final rebase after PR is marked "ready", but otherwise tend to cause annoying merge conflicts
5. PRs without test coverage for all logic will not be accepted

Small fixes by contributors who "own" (have recently made commits on) the part of the project they are making changes on may be fast-tracked, but when in doubt open at least a PR with a descriptive title **and** description.

Running on Windows
-------

https://github.com/FAForever/client/wiki/Windows-Dev-Py36

Running on Linux
-------
This guide is about runnning the client from source repository. For a [ready-made Arch-Linux package](https://aur.archlinux.org/cgit/aur.git/tree/PKGBUILD?h=python-fafclient) [follow the instructions in the wiki](http://wiki.faforever.com/index.php?title=Setting_Up_FAF_Linux).

Clone this repository locally:

    git clone https://github.com/FAForever/client.git faf-client

Create a python3(!) virtualenv for installing its dependencies:

    virtualenv ./faf-client-venv --system-site-packages
    ./faf-client-venv/bin/pip install -r ./faf-client/requirements.txt

**Note that many distributions have separate names for Python 2 and Python 3 virtualenv, such as "virtualenv" and "virtualenv3" - ensure you're using the Python 3 specific version on your distribution!**

Now download the `faf-uid` executable:

    wget https://github.com/FAForever/uid/releases/download/v4.0.4/faf-uid -O ./faf-client/lib/faf-uid
    chmod +x ./faf-client/lib/faf-uid

Note that the `faf-uid` smurf protection executable needs to run `xrandr`, `lspci`, `lsblk` and `uname` to gather unique system information. Additionally the `lsblk` command must support the "--json" flag, which was added in util-linux-2.27.

Run the client:

    cd ./faf-client && PATH=$PATH:./lib ../faf-client-venv/bin/python src/__main__.py

For more information see [the wiki](http://wiki.faforever.com/index.php?title=Setting_Up_FAF_Linux).

Running unit tests
-------
Before running unit tests, set PYTEST_QT_API as follows:

    export PYTEST_QT_API='pyqt5'

Run the lobby from the main directory using:

    python3 src

Run the unit test suite using:

    python3 runtests.py


License
-------

GPLv3. See the [license](license.txt) file.
