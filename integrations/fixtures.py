import pytest

from bw.server import app


@pytest.fixture(scope='function')
def test_app():
    yield app.test_client()
