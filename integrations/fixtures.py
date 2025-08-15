import alembic
import alembic.config
import pytest

from sqlalchemy.sql import text

from bw.state import State
from bw.server import app


@pytest.fixture(scope='function')
def state():
    return State()


@pytest.fixture(scope='function')
def session(request, state):
    try:
        # Create a temporary DB to do tests in. Per-test
        alembic_cfg = alembic.config.Config(toml_file='./pyproject.toml')

        test_db_name = f'bw_integration__{request.node.name}'
        with state.Engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
            conn.execute(text('COMMIT'))
            conn.execute(text(f'CREATE DATABASE {test_db_name}'))

        original_default = state.default_database
        state.register_database(test_db_name)
        state.default_database = test_db_name
        with state.Engine.connect() as session:
            alembic_cfg.attributes['connection'] = session
            alembic.command.upgrade(alembic_cfg, 'heads')
            yield session
        state.Engine.dispose()
    finally:
        # Drop database; unneeded after test
        state.default_database = original_default
        with state.Engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
            conn.execute(text('COMMIT'))
            conn.execute(text(f'DROP DATABASE {test_db_name}'))


@pytest.fixture(scope='function')
def test_app():
    yield app.test_client()
