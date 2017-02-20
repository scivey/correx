#!/bin/bash

. $(dirname ${BASH_SOURCE[0]})/common.sh

pushd ${CORREX_ROOT}
exec python -m correx.app.run
