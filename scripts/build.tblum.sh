#!/bin/bash

set -e

{

export USE_COMPILER=clang

./scripts/setenv.default.sh
./scripts/qcore.sh

./scripts/fftw.sh
./scripts/cuba.sh
./scripts/zlib.sh
./scripts/eigen.sh
./scripts/qlat-utils.sh
./scripts/qlat.sh

./scripts/c-lime.sh
./scripts/hdf5.sh
./scripts/grid-tblum.avx2.sh
./scripts/hadrons-tblum.sh
# ./scripts/gpt.sh

} 2>&1 | tee $prefix/log.build.txt
