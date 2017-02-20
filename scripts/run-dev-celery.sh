#!/bin/bash

. $(dirname ${BASH_SOURCE[0]})/common.sh

pushd ${CORREX_ROOT}

exec celery worker \
    -A correx.work.conf \
    -E
