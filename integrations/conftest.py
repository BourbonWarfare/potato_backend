import pytest
import logging
import secrets

from sqlalchemy.sql import text

from bw.state import State


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
        logging.debug(f'CREATE DATABASE {test_db_name}')
        with state.Engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
            conn.execute(text('COMMIT'))
            conn.execute(text(f'CREATE DATABASE {test_db_name}'))

        state.register_database(test_db_name)
        state.default_database = test_db_name

        yield state
    finally:
        # Drop database to be clean :)
        state.default_database = original_default
        logging.debug(f'DROP DATABASE {test_db_name}')
        with state.Engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
            conn.execute(text('COMMIT'))
            conn.execute(text(f'DROP DATABASE {test_db_name}'))
