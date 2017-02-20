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

function correx-ensure-venv() {
    if [[ ! -d ${CORREX_VENV_DIR} ]]; then
        pushd ${CORREX_ROOT}
        virtualenv ${CORREX_VENV_DIR}
        . ${CORREX_VENV_DIR}/bin/activate && pip install -r correx/requirements.txt
        popd
    fi
}

function correx-activate-venv() {
    if [[ ! -d ${CORREX_VENV_DIR} ]]; then
        echo "Expected virtualenv at '${CORREX_VENV_DIR}', but did not find it." >&2
        echo "Creating it; please wait." >&2
        correx-ensure-venv
    fi
    . ${CORREX_VENV_DIR}/bin/activate
    export PYTHONPATH="${CORREX_ROOT}:${PYTHONPATH}"
}
