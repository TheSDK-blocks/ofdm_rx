#!/usr/bin/env bash
DIR="$( cd "$( dirname $0 )" && pwd )"
cd $DIR

git submodule sync 
#for module in \
#    ./chisel; do
#    git submodule update --init $module
#    cd $module
#    if [ -f ./init_submodules.sh ]; then
#        ./init_submodules.sh
#        cd ${DIR}
#    fi
#done

exit 0



