#!/bin/bash

. $(dirname ${BASH_SOURCE[0]})/common.sh

pushd ${CORREX_ROOT}
correx-activate-venv
export CORREX_CONTEXT_TYPE=FLASK

HTTP_PORT="$1"

if [[ "${SERVER_HTTP_PORT}" == "" ]]; then
    SERVER_HTTP_PORT="9020"
fi

UWSGI_FLAGS="--http 127.0.0.1:${SERVER_HTTP_PORT} \
    --module correx.flask_app \
    --callable app \
    --enable-threads \
    --master \
    -p 4
"

# UWSGI_FLAGS="${UWSGI_FLAGS} --py-autoreload 1"

exec uwsgi ${UWSGI_FLAGS}
