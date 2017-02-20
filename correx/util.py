import shortuuid
import uuid
import flask
from cached_property import cached_property

def make_id():
    return shortuuid.encode(uuid.uuid4())


class Correlated(object):
    @cached_property
    def correlation_id(self):
        return make_id()

