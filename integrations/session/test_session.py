import datetime

import pytest
from sqlalchemy import select, update

from bw.error import NoSessionsRegistered, SessionAlreadyEnded, SessionDoesNotExist
from bw.models.session import Session
from bw.session.session import SessionStore
from bw.settings import TIMEZONE


def test__create_session__inserted_into_db(state, session):
    """Test that create_session inserts a new session row."""
    # Not yet reviewed
    arma_session = SessionStore().create_session(state)

    with state.Session.begin() as db_session:
        stored_session = db_session.execute(select(Session).where(Session.uuid == arma_session.uuid)).scalar_one()
        stored_uuid = stored_session.uuid
        stored_finish_date = stored_session.finish_date

    assert stored_uuid == arma_session.uuid
    assert stored_finish_date is None


def test__create_session__creates_unique_uuids(state, session):
    """Test that create_session creates unique UUIDs for separate sessions."""
    # Not yet reviewed
    session_1 = SessionStore().create_session(state)
    session_2 = SessionStore().create_session(state)

    assert session_1.uuid != session_2.uuid


def test__end_session__finish_updated(state, session):
    """Test that end_session sets a finish date on the requested session."""
    # Not yet reviewed
    arma_session = SessionStore().create_session(state)

    SessionStore().end_session(state, arma_session.uuid)

    with state.Session.begin() as db_session:
        stored_session = db_session.execute(select(Session).where(Session.uuid == arma_session.uuid)).scalar_one()
        stored_finish_date = stored_session.finish_date

    assert stored_finish_date is not None


def test__end_session__already_finished_raises(state, session):
    """Test that end_session raises when the session is already finished."""
    # Not yet reviewed
    arma_session = SessionStore().create_session(state)
    SessionStore().end_session(state, arma_session.uuid)

    with pytest.raises(SessionAlreadyEnded):
        SessionStore().end_session(state, arma_session.uuid)


def test__end_session__no_session_raises(state, session):
    """Test that end_session raises for an unknown session UUID."""
    # Not yet reviewed
    arma_session = SessionStore().create_session(state)
    SessionStore().end_session(state, arma_session.uuid)

    with pytest.raises(SessionDoesNotExist):
        SessionStore().end_session(state, arma_session.uuid.__class__(int=0))


def test__end_session__does_not_mutate_other_sessions(state, session):
    """Test that end_session only finishes the requested session."""
    # Not yet reviewed
    session_1 = SessionStore().create_session(state)
    session_2 = SessionStore().create_session(state)

    SessionStore().end_session(state, session_1.uuid)

    with state.Session.begin() as db_session:
        stored_session_2 = db_session.execute(select(Session).where(Session.uuid == session_2.uuid)).scalar_one()
        stored_session_2_finish_date = stored_session_2.finish_date

    assert stored_session_2_finish_date is None


def test__get_latest_session__happy_path__returns_latest_session(state, session):
    """Test that get_latest_session returns an active session."""
    # Not yet reviewed
    older_session = SessionStore().create_session(state)
    latest_session = SessionStore().create_session(state)
    with state.Session.begin() as db_session:
        db_session.execute(
            update(Session)
            .where(Session.uuid == older_session.uuid)
            .values(start_date=datetime.datetime(2024, 1, 1, tzinfo=TIMEZONE))
        )
        db_session.execute(
            update(Session)
            .where(Session.uuid == latest_session.uuid)
            .values(start_date=datetime.datetime(2024, 1, 2, tzinfo=TIMEZONE))
        )

    returned_session = SessionStore().get_latest_session(state)

    assert returned_session.uuid == latest_session.uuid


def test__get_latest_session__ignores_finished_sessions(state, session):
    """Test that get_latest_session ignores sessions that have ended."""
    # Not yet reviewed
    finished_session = SessionStore().create_session(state)
    active_session = SessionStore().create_session(state)
    SessionStore().end_session(state, finished_session.uuid)

    returned_session = SessionStore().get_latest_session(state)

    assert returned_session.uuid == active_session.uuid


def test__get_latest_session__no_sessions__raises(state, session):
    """Test that get_latest_session raises when no active sessions exist."""
    # Not yet reviewed
    with pytest.raises(NoSessionsRegistered):
        SessionStore().get_latest_session(state)


def test__session_with_uuid__happy_path__session_returned(state, session):
    """Test that session_with_uuid returns the requested session."""
    # Not yet reviewed
    arma_session = SessionStore().create_session(state)

    returned_session = SessionStore().session_with_uuid(state, arma_session.uuid)

    assert returned_session.uuid == arma_session.uuid


def test__session_with_uuid__no_uuid__exception_raised(state, session):
    """Test that session_with_uuid raises for an unknown UUID."""
    # Not yet reviewed
    arma_session = SessionStore().create_session(state)

    with pytest.raises(SessionDoesNotExist):
        SessionStore().session_with_uuid(state, arma_session.uuid.__class__(int=0))
