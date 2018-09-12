#!/bin/bash
set -e

if [[ -z ${VIRTUAL_ENV} ]]; then
	echo 'Run this into a ${VIRTUAL_ENV}'
	exit 1
fi

export LIBGIT2="${VIRTUAL_ENV}"

wget https://github.com/libgit2/libgit2/archive/v0.27.0.tar.gz
tar xzf v0.27.0.tar.gz
cd libgit2-0.27.0/
cmake . -DCMAKE_INSTALL_PREFIX=$LIBGIT2
make
make install

export LDFLAGS="-Wl,-rpath='$LIBGIT2/lib',--enable-new-dtags $LDFLAGS"
pip install pygit2==0.27.0
