import alembic
import alembic.config
import pytest
import logging

from sqlalchemy.sql import text

from bw.state import State
from bw.server import app


@pytest.hookimpl(tryfirst=True)
def pytest_keyboard_interrupt(excinfo):
    _pytestmark = pytest.mark.skip('Interrupted Test Session')


@pytest.fixture(scope='function')
def state():
    yield State()


@pytest.fixture(scope='session')
def test_database(request, state):
    original_default = state.default_database
    test_db_name = 'bw_integration'
    try:
        # Create a temporary DB to do tests in
        logging.info(f'CREATE DATABASE {test_db_name}')
        with state.Engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
            conn.execute(text('COMMIT'))
            conn.execute(text(f'CREATE DATABASE {test_db_name}'))

        state.register_database(test_db_name)
        state.default_database = test_db_name

        yield
        state.Engine.dispose()
    finally:
        # Drop database to be clean :)
        state.default_database = original_default
        logging.info(f'DROP DATABASE {test_db_name}')
        with state.Engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
            conn.execute(text('COMMIT'))
            conn.execute(text(f'DROP DATABASE {test_db_name}'))


@pytest.fixture(scope='function')
def session(request, state):
    # temporarily create tables for test. downgrade immediately after
    alembic_cfg = alembic.config.Config(toml_file='./pyproject.toml')
    logging.info('alembic upgrade head')
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
