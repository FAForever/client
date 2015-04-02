#!/bin/sh

# Install libgit2 from source and pip-install pygit2
echo "Installing libgit2"
wget https://github.com/libgit2/libgit2/archive/v0.22.0.tar.gz
tar xzf v0.22.0.tar.gz
cd libgit2-0.22.0/
cmake -Wno-dev .
make --quiet
sudo make install --quiet
sudo ldconfig
sudo pip install pygit2
python -c "import pygit2;print('SUCCESS')" 
