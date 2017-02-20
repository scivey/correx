#!/bin/bash

function pushd() {
    command pushd $@ &> /dev/null
}

function popd() {
    command popd $@ &> /dev/null
}

pushd $(dirname ${BASH_SOURCE[0]})
export CORREX_SCRIPTS=$(pwd)
popd
pushd ${CORREX_SCRIPTS}/..
export CORREX_ROOT=$(pwd)
popd
export CORREX_TEMP=${CORREX_ROOT}/tmp
export CORREX_VENV_DIR=${CORREX_ROOT}/.env
