#!/bin/bash

. scripts/res/conf.sh

name=setenv

mkdir -p "$prefix"

{

echo "!!!! build $name !!!!"

cat - scripts/res/setenv.sh >"$prefix/setenv.sh" << EOF
echo "Sourcing '$prefix/setenv.sh'"
export prefix="$prefix"
if [ -z "\$num_proc" ] ; then
    num_proc=4
fi
source /etc/profile
module purge
module add modules
module add pre-module
module add post-module
module add vim/8.1
module add git/2.27.0
module add gcc/9.2.0
module add mpi/openmpi/4.0.3
module list
EOF

./scripts/setup-scripts.sh

. "$prefix/setenv.sh" >"$prefix/log.setenv.txt" 2>&1

echo "!!!! $name build !!!!"

rm -rf $temp_dir || true

} 2>&1 | tee $prefix/log.$name-build.txt
