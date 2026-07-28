import logging
import secrets
from math import ceil

from bw.error import CannotDetermineSession
from bw.models.auth import TOKEN_LENGTH

logger = logging.getLogger('bw.auth')


def secure_token_urlsafe(length: int = TOKEN_LENGTH) -> str:
    needed_bytes = ceil(3 * length / 4)
    return secrets.token_urlsafe(needed_bytes)[:length]


def session_token_from_bearer(headers) -> str:
    auth = headers.get('Authorization')
    if auth is None:
        logger.warning("'Session Token' not present in header")
        raise CannotDetermineSession()

    bearer_header = 'Bearer '
    if not auth.startswith(bearer_header):
        logger.warning("'Session Token' does not start with 'Bearer '")
        raise CannotDetermineSession()

    return auth[len(bearer_header) :]  # Remove 'Bearer ' prefix


def session_token_from_cookie(api) -> str:
    return api.get_session_cookie()
