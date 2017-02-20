#!/bin/bash

. $(dirname ${BASH_SOURCE[0]})/common.sh

function clean-one() {
    local dname="$1"
    if [[ "${dname}" == "" ]]; then
        echo "invalid clean-one target: '${dname}'" >&2
        return 1
    fi
    find ${dname} -name "*.pyc" | xargs rm -f
    find ${dname} -name "__pycache__" | xargs rm -rf
}

function clean-it() {
    pushd ${CORREX_ROOT}
    local names="correx      scripts"
    for dname in ${names}; do
        clean-one ${dname}
    done
    popd    
}

clean-it
