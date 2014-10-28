#!/bin/sh

# Install libgit2 from a bunch of Ubuntu 15.04 binary repos
mkdir libgit2
pushd libgit2

wget -q --progress=bar "https://launchpad.net/ubuntu/+source/libgit2/0.21.1-1/+build/6494190/+files/libgit2-21_0.21.1-1_amd64.deb"
wget -q --progress=bar "https://launchpad.net/ubuntu/+source/libgit2/0.21.1-1/+build/6494190/+files/libgit2-dev_0.21.1-1_amd64.deb"

sudo dpkg -i "libgit2-21_0.21.1-1_amd64.deb"
sudo dpkg -i "libgit2-dev_0.21.1-1_amd64.deb"

popd
