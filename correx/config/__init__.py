from __future__ import print_function
import os
import redis
import logging.config
import logging
import threading
import psycopg2
from psycopg2.extras import NamedTupleCursor
from copy import deepcopy
from cytoolz import memoize

class _RedisConf(object):
    host = 'localhost'
    port = 6381
    celery_db = 11

    def __getattr__(self, name):
        as_db_num_attr = name + '_db'
        if hasattr(self, as_db_num_attr):
            fact = RedisFactory(
                host=self.host,
                port=self.port,
                db=getattr(self, as_db_num)
            )
            setattr(self, name, fact)
            return fact
        raise AttributeError(name)

    @property
    def broker_url(self):
        return 'redis://{}:{}/{}'.format(self.host, self.port, self.celery_db)



class _PostgresConf(object):
    host = 'localhost'
    port = 5436
    user = 'correx_user'
    password = 'correx_passwd'
    db = 'correx_db'

    @property
    def dsn(self):
        return 'postgresql://{user}:{password}@{host}:{port}/{db}'.format(
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            db=self.db
        )

    def connect(self):
        from correx import pg_lib
        return pg_lib.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.db
        )

    def query_inspector(self):
        from correx import pg_lib
        return pg_lib.QueryInspector(self.connect())

    def inspect(self):
        return list(self.query_inspector().inspect())



class ContextType(object):
    FLASK = 'FLASK'
    CELERY = 'CELERY'
    SHELL = 'SHELL'

    allowed = frozenset([FLASK, CELERY, SHELL])


class _Configurator(object):
    redis = _RedisConf()
    postgres = _PostgresConf()
    _logging_initialized = False

    def setup_logging(self):
        from .logs import setup_logging as sub_setup_logging
        if not self._logging_initialized:
            sub_setup_logging()
            self._logging_initialized = True

    @property
    def context_type(self):
        ctx_type = os.getenv('CORREX_CONTEXT_TYPE', ContextType.SHELL).upper()
        assert ctx_type in ContextType.allowed
        return ctx_type


@memoize
def get_config():
    return _Configurator()



