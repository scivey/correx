import os
import json
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

    START = '__META_START'
    END = 'META_END__'

    @classmethod
    def decode(cls, query):
        try:
            start = query.index(cls.START) + len(cls.START)
            end = query.index(cls.END, start)

            # adjust for colons
            start += 1
            end -= 1
        except ValueError:
            # substr not found
            raise cls.DecodeError(query)
        return query[start:end]

    @classmethod
    def encode(cls, **kwargs):
        dumped = json.dumps(kwargs).strip()
        return '/* %s:%s:%s  */  ' % (
            cls.START, dumped, cls.END
        )



class CorrelationIDCursor(NamedTupleCursor):
    conn_correlation_id = None

    @cached_property
    def correlation_id(self):
        return make_id()

    def execute(self, query, vars=None):
        from sec2.app.common import get_request_id_or_none
        from sec2.work.util import get_current_task_id_or_none
        metadata = dict(
            conn_id=self.conn_correlation_id,
            cursor_id=self.correlation_id,
            client_pid=os.getpid(),
            flask_req_id=get_flask_request_id_or_none(),
            celery_task_id=get_celery_task_id_or_none()
        )
        metadata = MetadataCodec.encode(**metadata)

        # if query was 'select 1;',
        # final_query is '/* __META_START:{"x": "x-val"}:META_END__ */ select 1;'
        final_query = metadata + query

        return super(CorrIdCursor, self).execute(final_query, vars=vars)


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

    def inspect(self):
        with self.conn.cursor() as c:
            c.execute("select * from pg_catalog.pg_stat_activity")
            for row in c.fetchall():
                try:
                    meta = MetadataCodec.decode(row.query)
                except MetadataCodec.DecodeError:
                    meta = None
                yield meta, row
