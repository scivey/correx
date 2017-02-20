from __future__ import print_function
import logging
import logging.config
import random
import contextlib
from copy import deepcopy
from cached_property import cached_property
import flask

class FlaskLogFilter(logging.Filter):
    """
    adds the correlation id of current flask
    request, if any, to log records
    """
    def filter(self, record):
        from correx.flask_lib import get_current_flask_request_id_or_none
        corr_id = get_current_flask_request_id_or_none()
        record.correlation_id = corr_id or 'NONE'
        return True


class CeleryLogFilter(logging.Filter):
    """
    adds the task id of current celery
    task, if any, to log records
    """
    def filter(self, record):
        from correx.celery_app import get_current_celery_task_id_or_none
        corr_id = get_current_celery_task_id_or_none()
        record.correlation_id = corr_id or 'NONE'
        return True


class _LogFormat(object):
    PLAIN = '%(asctime)s %(name)s %(levelname)s - %(message)s'
    FLASK = PLAIN + ' [FLASK_CID:%(correlation_id)s]'
    CELERY = PLAIN + ' [CELERY_CID:%(correlation_id)s]'





_BASE_LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': True,
    'filters': {},
    'formatters': {
        'plain': {
            'format': _LogFormat.PLAIN
        },
        'flask': {
            'format': _LogFormat.FLASK
        },
        'celery': {
            'format': _LogFormat.CELERY
        }
    },
    'filters': {
        'flask_app': {
            '()': FlaskLogFilter
        },
        'celery_app': {
            '()': CeleryLogFilter
        }
    },
    'handlers': {
        'flask_console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'flask',
            'filters': ['flask_app']
        },
        'celery_console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'celery',
            'filters': ['celery_app']
        },        
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'plain',
            'filters': []
        }
    },
    'loggers': {}
}



def setup_logging():
    from . import get_config, ContextType

    _CONTEXT_TYPE_TO_HANDLER = {
        ContextType.FLASK: 'flask_console',
        ContextType.CELERY: 'celery_console',
        ContextType.SHELL: 'console'
    }

    app_config = get_config()
    log_conf = deepcopy(_BASE_LOG_CONFIG)
    log_conf['loggers'] = {
        '': {
            'handlers': [_CONTEXT_TYPE_TO_HANDLER[app_config.context_type]],
            'level': 'INFO',
            'propagate': True            
        }
    }
    logging.config.dictConfig(log_conf)

