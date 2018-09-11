
export LIBGIT2="${VIRTUAL_ENV}"
export LDFLAGS="-Wl,-rpath='$LIBGIT2/lib',--enable-new-dtags $LDFLAGS"
export LD_LIBRARY_PATH=$LIBGIT2/lib
