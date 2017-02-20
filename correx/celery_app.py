from __future__ import print_function
from pprint import pprint
from cached_property import cached_property
from datetime import datetime, timedelta
import logging
from celery import Celery
from kombu import Queue, Exchange
import celery
from celery import signals

CELERY_QUEUE = 'celery'

class CeleryConfig(object):
    BROKER_TRANSPORT_OPTIONS = {
        'visibility_timeout': 2 * 3600 # 2 hours
    }
    CELERY_QUEUES = [
        Queue(CELERY_QUEUE, Exchange(CELERY_QUEUE), routing_key=CELERY_QUEUE),
    ]

    @cached_property
    def correx_config(self):
        from correx.config import get_config
        return get_config()

    @property
    def BROKER_URL(self):
        return self.correx_config.redis.broker_url

    @property
    def CELERY_RESULT_BACKEND(self):
        return self.BROKER_URL

    CELERY_TASK_RESULT_EXPIRES = timedelta(hours=1)

    CELERYD_TASK_SOFT_TIME_LIMIT = 300
    CELERYD_TASK_TIME_LIMIT = 330

    CELERY_TASK_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json', 'pickle']

    CELERY_SEND_TASK_SENT_EVENT = True
    CELERY_TIMEZONE = 'UTC'
    CELERYD_HIJACK_ROOT_LOGGER = False


correx_celery = Celery('correx', config_source=CeleryConfig())

@signals.setup_logging.connect
def setup_celery_logging(*args, **kwargs):
    from correx.config import get_config
    get_config().setup_logging()


def get_current_celery_task_id_or_none():
    current_task = correx_celery.current_worker_task
    if current_task is not None:
        return current_task.request.id


@correx_celery.task(queue=CELERY_QUEUE)
def pg_sleep_in_worker(seconds):
    logger = logging.getLogger('%s.pg_sleep_in_worker' % __name__)
    try:
        from correx.pg_lib import pg_sleep
        logger.info("seconds=%r", seconds)
        pg_sleep(seconds)
        logger.info("done with pg_sleep(%r)", seconds)
        return {
            'status': 'OK',
            'celery_task_id': get_current_celery_task_id_or_none(),
            'seconds': seconds
        }
    except Exception as err:
        logger.error("error! %r", exc_info=True)
        raise

