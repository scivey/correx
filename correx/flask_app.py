import os
import flask
from flask import request
from werkzeug.contrib.fixers import ProxyFix
from correx.config import get_config
from correx.flask_lib import CorrelatedRequest
import logging


get_config().setup_logging()
app = flask.Flask('correx')
app.wsgi_app = ProxyFix(app.wsgi_app)
app.request_class = CorrelatedRequest


def _get_sleep_seconds():
    return int(request.args.get('seconds', 15))

def jsonify_with_request_id(**kwargs):
    from correx.flask_lib import get_current_flask_request_id_or_none    
    return flask.jsonify(
        flask_request_id=get_current_flask_request_id_or_none(),
        **kwargs
    )

@app.route('/api/v1/sleep-in-worker')
def db_sleep_in_worker():
    from correx.celery_app import pg_sleep_in_worker
    logger = logging.getLogger('%s.db_sleep_in_worker' % __name__)
    sleep_duration = _get_sleep_seconds()
    logger.info("triggering celery task to run pg_sleep(%r)", sleep_duration)

    task_future = pg_sleep_in_worker.delay(sleep_duration)
    logger.info("waiting for result of pg_sleep_in_worker(%r). Task id is %r", 
        sleep_duration, task_future.id
    )
    task_result = task_future.get()
    logger.info("got result for remote pg_sleep(%r)", sleep_duration)
    return jsonify_with_request_id(
        task_result=task_result
    )



@app.route('/api/v1/sleep-in-web')
def db_sleep_in_web():
    from correx.pg_lib import pg_sleep
    logger = logging.getLogger('%s.db_sleep_in_web' % __name__)
    sleep_duration = _get_sleep_seconds()
    logger.info("calling pg_sleep(%r)", sleep_duration)
    pg_sleep(sleep_duration)
    return jsonify_with_request_id(
        status='OK',
        seconds=sleep_duration
    )


@app.route('/api/v1/inspect-db')
def inspect_db():
    logger = logging.getLogger(__name__)
    queries = get_config().postgres.inspect()
    return jsonify_with_request_id(
        queries=get_config().postgres.inspect()
    )


if __name__ == '__main__':
    app.run('127.0.0.1', port=5001, debug=True)
