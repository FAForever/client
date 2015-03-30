#!/bin/sh

# Install libgit2 from source and pip-install pygit2
wget https://github.com/libgit2/libgit2/archive/v0.22.0.tar.gz
tar xzf v0.22.0.tar.gz
cd libgit2-0.22.0/
cmake .
make
sudo make install
pip install pygit2
sudo ldconfig
python -c 'import pygit2;print("SUCCESS")'
