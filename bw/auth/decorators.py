import logging
from bw.error import NonLocalIpAccessingLocalOnlyAddress, SessionInvalid
from bw.state import State
from bw.auth.validators import validate_local, validate_session
from quart import request

logger = logging.getLogger('wsgilog.log')


def require_local(func):
    """
    ### Restrict access to local network requests

    Decorator that restricts access to the decorated function to local network requests only.
    If the request is not from a local IP, returns a 401 response and logs a warning.
    """

    def wrapper(*args, **kwargs):
        try:
            validate_local(request.remote_addr)
        except NonLocalIpAccessingLocalOnlyAddress as e:
            logger.warning(f'Non-local API called from abroad: {e}')
            return e.as_response_code()
        return func(*args, **kwargs)

    return wrapper


def require_session(func):
    """
    ### Require a valid session token

    Decorator that ensures the decorated function is called with a valid session token.
    If the session token is missing or invalid, returns a 403 response.
    """

    def wrapper(*args, **kwargs):
        if 'session_token' not in kwargs:
            return SessionInvalid().as_response_code()

        session_token = kwargs['session_token']
        try:
            validate_session(State.state, session_token)
        except SessionInvalid as e:
            return e.as_response_code()
        return func(*args, **kwargs)

    return wrapper


def require_group_permission(*permissions):
    """
    ### Require group permissions

    Decorator factory for requiring group permissions. (Implementation placeholder)
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator
