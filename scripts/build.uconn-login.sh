#!/bin/bash

set -e

{

./scripts/setenv.default.sh

./scripts/xz.sh
./scripts/tar.sh
./scripts/gsl.sh
./scripts/gmp.sh
./scripts/mpfr.sh
./scripts/mpc.sh
./scripts/gcc.sh
./scripts/binutils.sh
./scripts/perl.sh
./scripts/openssl.sh
./scripts/libffi.sh
./scripts/zlib.sh
./scripts/openblas.sh
./scripts/python.sh
./scripts/python-pip.sh
./scripts/re2c.sh
./scripts/ninja.sh
./scripts/python-meson.sh
./scripts/python-packages.sh

./scripts/openmpi.sh

./scripts/fftw_mpi.sh
./scripts/fftwf_mpi.sh
./scripts/cuba.sh
./scripts/eigen.sh
./scripts/qlat.sh

./scripts/autoconf.sh
./scripts/automake.sh
./scripts/c-lime.sh
./scripts/hdf5.sh
./scripts/grid.gen16.sh
./scripts/gpt.sh
./scripts/qlat-grid.sh

./scripts/gnuplot.sh

./scripts/cmake.sh
./scripts/llvm-project.sh

./scripts/python-jupyter.sh

} 2>&1 | tee $prefix/log.build.txt
