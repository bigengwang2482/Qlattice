#!/bin/bash

export USE_COMPILER=clang

name=qlat-utils

source qcore/set-prefix.sh $name

{ time {
    echo "!!!! build $name !!!!"
    source qcore/conf.sh ..

    build="$prefix/build-clang"
    mkdir -p "$build"

    cd "$build"

    if [ -n "$QLAT_CXX" ] ; then
        export CXX="$QLAT_CXX"
    fi
    if [ -n "$QLAT_CXXFLAGS" ] ; then
        export CXXFLAGS="$QLAT_CXXFLAGS"
    fi
    if [ -n "$QLAT_LDFLAGS" ] ; then
        export LDFLAGS="$QLAT_LDFLAGS"
    fi
    if [ -n "$QLAT_LIBS" ] ; then
        export LIBS="$QLAT_LIBS"
    fi

    touch "$wd"/qlat-utils/meson.build

    time-run meson setup "$wd/qlat-utils" \
        --prefix="$prefix" \
        -Dpython.platlibdir="$prefix/lib/python3/qlat-packages" \
        -Dpython.purelibdir="$prefix/lib/python3/qlat-packages"

    time-run meson compile -j$num_proc

    rm -rfv "$prefix"/lib
    time-run meson install

    mk-setenv.sh
    echo "!!!! $name build !!!!"
    rm -rf "$temp_dir" || true
} } 2>&1 | tee $prefix/log.$name.txt
