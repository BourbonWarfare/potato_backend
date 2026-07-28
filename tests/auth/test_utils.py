import pytest

from bw.auth.utils import secure_token_urlsafe, session_token_from_bearer, session_token_from_cookie
from bw.error import CannotDetermineSession


@pytest.fixture
def token() -> str:
    return 'abcdef'


def test__secure_token_urlsafe__returns_expected_length():
    token1 = secure_token_urlsafe(length=1000)
    token2 = secure_token_urlsafe(length=1)
    token3 = secure_token_urlsafe(length=3)
    token4 = secure_token_urlsafe(length=12)
    assert len(token1) == 1000
    assert len(token2) == 1
    assert len(token3) == 3
    assert len(token4) == 12


def test__session_token_from_bearer__retrieves_token(token):
    header = {'Authorization': f'Bearer {token}'}
    session_token = session_token_from_bearer(header)
    assert session_token == token


def test__session_token_from_bearer__no_bearer_raises(token):
    header = {'Authorization': 'Basic'}
    with pytest.raises(CannotDetermineSession):
        session_token_from_bearer(header)


def test__session_token_from_bearer__no_auth_header_raises(token):
    header = {}
    with pytest.raises(CannotDetermineSession):
        session_token_from_bearer(header)


def test__session_token_from_cookie__returns_token_from_api(token):
    class MockApi:
        def get_session_cookie(self) -> str:
            return token

    session_token = session_token_from_cookie(MockApi())
    assert session_token == token
