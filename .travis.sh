#!/bin/sh

sudo apt-get install cmake
pip install cffi

pushd

cd ~

git clone --depth=1 -b v0.21.1 https://github.com/libgit2/libgit2.git
cd libgit2/

mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=../_install -DBUILD_CLAR=OFF
cmake --build . --target install

ls -la ..

popd

sudo apt-get install python-qt4
pip install -r requirements.txt
