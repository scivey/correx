import os
import logging
import json
import getpass
from psycopg2.extras import (
    NamedTupleCursor,
    NamedTupleConnection
)
import psycopg2
from psycopg2.extensions import connection
from cached_property import cached_property
from correx.util import make_id

class MetadataCodec(object):

    class CodecError(RuntimeError):
        pass

    class DecodeError(CodecError):
        pass

    START = '/* __META_START'
    END = 'META_END__ */'

    @classmethod
    def decode(cls, query):
        try:
            meta_start = query.index(cls.START)
            meta_end = query.index(cls.END, meta_start)
        except ValueError:
            # substr not found
            raise cls.DecodeError(query)

        # adjust for colons
        meta_inner_start = meta_start + len(cls.START) + 1
        meta_inner_end = meta_end - 1

        json_blob = query[meta_inner_start:meta_inner_end]
        query_without_metadata = query[:meta_start].strip()
        try:
            return json.loads(json_blob), query_without_metadata
        except json.JSONDecodeError as err:
            raise cls.DecodeError(err)

    @classmethod
    def encode(cls, query, metadata):
        # if query was 'select 1;',
        # final_query is 'select 1;  /* __META_START:{"x": "x-val"}:META_END__ */'

        dumped = json.dumps(metadata).strip()
        tagged_metadata_str = '%s:%s:%s' % (
            cls.START, dumped, cls.END
        )
        return '%s  %s' % (query, tagged_metadata_str)



class CorrelationIDCursor(NamedTupleCursor):
    conn_correlation_id = None

    @cached_property
    def correlation_id(self):
        return make_id()

    def execute(self, query, vars=None):
        from correx.config import get_config
        from correx.flask_lib import get_current_flask_request_id_or_none
        from correx.celery_app import get_current_celery_task_id_or_none
        metadata = dict(
            pg_conn_id=self.conn_correlation_id,
            cursor_id=self.correlation_id,
            client_pid=os.getpid(),
            os_user=getpass.getuser(),
            flask_req_id=get_current_flask_request_id_or_none(),
            celery_task_id=get_current_celery_task_id_or_none(),
            context_type=get_config().context_type
        )

        # if query was 'select 1;',
        # final_query is '/* __META_START:{"x": "x-val"}:META_END__ */ select 1;'
        final_query = MetadataCodec.encode(query=query, metadata=metadata)

        return super(CorrelationIDCursor, self).execute(final_query, vars=vars)


class Connection(connection):
    @cached_property
    def correlation_id(self):
        return make_id()

    def cursor(self, *args, **kwargs):
        kwargs['cursor_factory'] = CorrelationIDCursor
        cursor = super(Connection, self).cursor(*args, **kwargs)
        cursor.conn_correlation_id = self.correlation_id
        return cursor



def connect(**kwargs):
    return psycopg2.connect(
        connection_factory=Connection,
        **kwargs
    )


class QueryInspector(object):
    def __init__(self, conn):
        self.conn = conn

    @cached_property
    def logger(self):
        return logging.getLogger(__name__ + '.QueryInspector')

    def inspect(self):
        with self.conn.cursor() as cursor:
            cursor.execute("select * from pg_catalog.pg_stat_activity")
            for row in cursor.fetchall():
                try:
                    metadata, query = MetadataCodec.decode(row.query)
                except MetadataCodec.DecodeError:
                    metadata, query = None, None

                if metadata and metadata.get('cursor_id') == cursor.correlation_id:
                    self.logger.debug("skipping result row for my own query on pg_stat_activity")
                    continue

                row_dict = dict(row._asdict())
                
                # the `query` key here contains the combined query and serialized metadata,
                # which is ugly. the `query` key in the object we're returning is the 
                # cleaned query, with the metadata removed 
                row_dict.pop('query')

                yield {
                    'app_metadata': metadata,
                    'query': query,
                    'db_metadata': row_dict
                }


def pg_sleep(sleep_seconds):
    from correx.config import get_config
    logger = logging.getLogger(__name__)

    logger.info("will send pg_sleep(%r) to postgres", sleep_seconds)
    pg_conn = get_config().postgres.connect()
    with pg_conn.cursor() as cursor:
        cursor.execute("select * from pg_sleep(%(seconds)s)", dict(seconds=sleep_seconds))
        logger.info("finished pg_sleep(%r)", sleep_seconds)
