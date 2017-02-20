#!/bin/bash

. $(dirname ${BASH_SOURCE[0]})/common.sh

pushd ${CORREX_ROOT}

if [[ ! -d ${CORREX_VENV_DIR} ]]; then
    virtualenv ${CORREX_VENV_DIR}
fi
. ${CORREX_VENV_DIR}/bin/activate
pip install -r correx/requirements.txt
