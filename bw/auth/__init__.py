import logging
import web
from web import webapi
from bw.error import NonLocalIpAccessingLocalOnlyAddress
from bw.configuration import Configuration
from bw.server import WebServer
from bw.auth.validators import validate_local

logger = logging.getLogger('wsgilog.log')

AUTH_SETTINGS = None
if AUTH_SETTINGS is None:
    AUTH_SETTINGS = Configuration.load('auth.txt')

def require_local(func):
    def wrapper(*args, **kwargs):
        try:
            validate_local(web.ctx)
        except NonLocalIpAccessingLocalOnlyAddress as e:
            logger.warning(f'Non-local API called from abroad: {e}')
            return webapi.forbidden()
        return func(*args, **kwargs)
    return wrapper

def require_session(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

def require_group_permission(*permissions):
    def decorator(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator
