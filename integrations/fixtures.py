import alembic
import alembic.config
import pytest
import logging

from bw.state import State
from bw.server import app


@pytest.fixture(scope='function')
def state(test_database):
    state = State()
    state.register_database(test_database.default_database)
    state.default_database = test_database.default_database
    try:
        yield state
    finally:
        while state.Engine.pool.checkedout() > 0:
            # wait for connections to time out
            pass
        state.Engine.dispose()


@pytest.fixture(scope='function')
def session(state, request):
    # temporarily create tables for test. downgrade immediately after
    alembic_cfg = alembic.config.Config(toml_file='./pyproject.toml')
    logging.debug('alembic upgrade head')
    with state.Engine.connect() as session:
        alembic_cfg.attributes['connection'] = session
        alembic.command.upgrade(alembic_cfg, 'head')
        try:
            yield session
        finally:
            alembic.command.downgrade(alembic_cfg, 'base')


@pytest.fixture(scope='function')
def test_app():
    yield app.test_client()
