import pytest

from bw.state import State


@pytest.fixture(scope='function')
def state(session):
    state = State()
    state.Session = session


@pytest.fixture(scope='function')
def session(state):
    session = state.Session.begin()
    savepoint = session.begin_nested()
    yield session
    savepoint.rollback()
    session.close()
