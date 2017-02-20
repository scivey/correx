#!/bin/bash

. $(dirname ${BASH_SOURCE[0]})/common.sh

pushd ${CORREX_ROOT}
correx-activate-venv
export CORREX_CONTEXT_TYPE=CELERY
exec celery worker \
    -A correx.celery_app \
    -E
