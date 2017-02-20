import flask

from .util import Correlated

class CorrelatedRequest(flask.Request, Correlated):
    pass

def get_current_flask_request_id_or_none():
    if flask.has_request_context():
        return flask.request.correlation_id


