import alembic
import alembic.config
import pytest

from sqlalchemy import insert
from sqlalchemy.sql import text

from bw.state import State
from bw.models.auth import User, Session


@pytest.fixture(scope='session')
def token_1():
    return 'token 1'


@pytest.fixture(scope='session')
def token_2():
    return 'token 2'


@pytest.fixture(scope='session')
def expire_valid():
    return '9999-12-23 02:11:06'


@pytest.fixture(scope='session')
def expire_invalid():
    return '1999-12-23 02:11:06'


@pytest.fixture(scope='function')
def state():
    return State()


@pytest.fixture(scope='function')
def session(request, state):
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

    # Drop database; unneeded after test
    state.default_database = original_default
    with state.Engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
        conn.execute(text('COMMIT'))
        conn.execute(text(f'DROP DATABASE {test_db_name}'))


@pytest.fixture(scope='function')
def db_user_1(state, session):
    with state.Session.begin() as session:
        query = insert(User).values(id=1).returning(User)
        user = session.execute(query).first()[0]
        session.expunge(user)
    yield user


@pytest.fixture(scope='function')
def db_session_1(state, session, db_user_1, token_1):
    with state.Session.begin() as session:
        query = insert(Session).values(id=1, user_id=db_user_1.id, token=token_1).returning(Session)
        user_session = session.execute(query).first()[0]
        session.expunge(user_session)
    yield user_session
