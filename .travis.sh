#!/bin/sh

cd ~

git clone --depth=1 -b v0.21.1 https://github.com/libgit2/libgit2.git
cd libgit2/

mkdir build && cd build
cmake ..
cmake --build .
cmake --target install

cd ~

sudo apt-get install python-qt4
