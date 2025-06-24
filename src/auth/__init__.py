import logging
import web
from web import webapi
from error import NonLocalIpAccessingLocalOnlyAddress
from configuration import Configuration

logger = logging.getLogger('wsgilog.log')

AUTH_SETTINGS = None
if AUTH_SETTINGS is None:
    AUTH_SETTINGS = Configuration.load('auth.txt')


def verify_local(ctx: dict):
    valid_local_prefix = (
        '0.',
        '10.',
        '127.',
        '172.16.',
        '192.0.0.',
        '192.168.',
    )
    ip = ctx.get('ip', '255.255.255.255')
    if not any([ip.startswith(prefix) for prefix in valid_local_prefix]):
        raise NonLocalIpAccessingLocalOnlyAddress(ip)

def require_local(func):
    def wrapper(*args, **kwargs):
        try:
            verify_local(web.ctx)
        except NonLocalIpAccessingLocalOnlyAddress as e:
            logger.warning(f'Non-local API called from abroad: {e}')
            return webapi.forbidden()
        return func(*args, **kwargs)
    return wrapper