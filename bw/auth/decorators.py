import logging
import web
from bw.error import NonLocalIpAccessingLocalOnlyAddress, SessionInvalid
from bw.server import WebServer
from bw.auth.validators import validate_local, validate_session

logger = logging.getLogger('wsgilog.log')

def require_local(func):
    def wrapper(*args, **kwargs):
        try:
            validate_local(web.ctx)
        except NonLocalIpAccessingLocalOnlyAddress as e:
            logger.warning(f'Non-local API called from abroad: {e}')
            return e.as_response_code()
        return func(*args, **kwargs)
    return wrapper

def require_session(func):
    def wrapper(*args, **kwargs):
        if 'session_token' not in kwargs:
            return SessionInvalid().as_response_code()

        session_token = kwargs['session_token']
        try:
            validate_session(WebServer.state, session_token)
        except SessionInvalid as e:
            return e.as_response_code()
        return func(*args, **kwargs)
    return wrapper

def require_group_permission(*permissions):
    def decorator(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator