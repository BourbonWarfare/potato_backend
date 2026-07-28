import logging
import secrets

import alembic.config
import pytest
from sqlalchemy.sql import text

import alembic
from bw.state import State

logger = logging.getLogger()


@pytest.hookimpl(tryfirst=True)
def pytest_keyboard_interrupt(excinfo):
    _pytestmark = pytest.mark.skip('Interrupted Test Session')


@pytest.fixture(scope='session')
def test_database(request):
    state = State()
    original_default = state.default_database
    test_db_name = f'bw_integration__{secrets.token_hex(24)}'
    try:
        # Create a temporary DB to do tests in
        logger.debug(f'CREATE DATABASE {test_db_name}')
        with state.Engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
            conn.execute(text('COMMIT'))
            conn.execute(text(f'CREATE DATABASE {test_db_name}'))

        state.register_database(test_db_name)
        state.default_database = test_db_name

        yield state
    finally:
        # Drop database to be clean :)
        state.default_database = original_default
        logger.debug(f'DROP DATABASE {test_db_name}')
        with state.Engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
            conn.execute(text('COMMIT'))
            conn.execute(text(f'DROP DATABASE {test_db_name}'))


@pytest.fixture(scope='function', autouse=True)
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


@pytest.fixture(scope='function', autouse=True)
def session(state, request):
    # temporarily create tables for test. downgrade immediately after
    alembic_cfg = alembic.config.Config(toml_file='./pyproject.toml')
    logger.debug('alembic upgrade head')
    with state.Engine.connect() as session:
        alembic_cfg.attributes['connection'] = session
        alembic.command.upgrade(alembic_cfg, 'head')
        try:
            yield session
        finally:
            alembic.command.downgrade(alembic_cfg, 'base')
