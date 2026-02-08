# ruff: noqa: F811, F401

import pytest
from datetime import datetime

from sqlalchemy import select

from bw.auth.session import SessionStore
from bw.models.auth import Session, DiscordOAuthCode
from bw.error import SessionExpired, NoAccessCodeFound
from integrations.auth.fixtures import (
    state,
    session,
    db_user_1,
    db_session_1,
    token_1,
    token_2,
    expire_valid,
    expire_invalid,
    db_user_2,
    db_session_2,
    oauth_code_1,
    oauth_code_2,
    oauth_code_3,
    oauth_state_1,
    oauth_state_2,
    oauth_state_3,
    db_oauth_code_1,
    db_oauth_code_2,
    db_oauth_code_expired,
)


def test__session_store__is_session_valid__no_session(state, session):
    assert not SessionStore().is_session_active(state, 'no token')


def test__session_store__is_session_valid__with_session(state, session, db_session_1, token_1):
    assert SessionStore().is_session_active(state, token_1)


def test__session_store__starting_session_return_correct(mocker, token_1, expire_valid, state, session, db_user_1):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    mocker.patch('bw.models.auth.Session.api_session_length', return_value=expire_valid)

    new_session = SessionStore().start_api_session(state, db_user_1)
    assert new_session['session_token'] == token_1
    assert datetime.fromisoformat(new_session['expire_time']) == datetime.fromisoformat(expire_valid)


def test__session_store__starting_session_activates(mocker, token_1, expire_valid, state, session, db_user_1):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    mocker.patch('bw.models.auth.Session.api_session_length', return_value=expire_valid)

    new_session = SessionStore().start_api_session(state, db_user_1)
    assert SessionStore().is_session_active(state, new_session['session_token'])


def test__session_store__starting_session_activates_with_db_value(mocker, state, session, db_user_1):
    new_session = SessionStore().start_api_session(state, db_user_1)
    assert SessionStore().is_session_active(state, new_session['session_token'])


def test__session_store__expired_session_is_invalid(mocker, token_1, expire_invalid, state, session, db_user_1):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    mocker.patch('bw.models.auth.Session.api_session_length', return_value=expire_invalid)

    new_session = SessionStore().start_api_session(state, db_user_1)
    assert not SessionStore().is_session_active(state, new_session['session_token'])


def test__session_store__expiring_stops_session(mocker, token_1, expire_valid, state, session, db_user_1):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    mocker.patch('bw.models.auth.Session.api_session_length', return_value=expire_valid)

    new_session = SessionStore().start_api_session(state, db_user_1)
    SessionStore().expire_session_from_user(state, db_user_1)
    assert not SessionStore().is_session_active(state, new_session['session_token'])


def test__session_store__safe_to_expire_non_session(mocker, token_1, expire_valid, state, session, db_user_1):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    mocker.patch('bw.models.auth.Session.api_session_length', return_value=expire_valid)

    SessionStore().expire_session_from_user(state, db_user_1)


def test__session_store__many_sessions_only_latest_valid(mocker, token_1, token_2, expire_valid, state, session, db_user_1):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    mocker.patch('bw.models.auth.Session.api_session_length', return_value=expire_valid)

    first_session = SessionStore().start_api_session(state, db_user_1)

    mocker.patch('secrets.token_urlsafe', return_value=token_2)
    second_session = SessionStore().start_api_session(state, db_user_1)

    assert not SessionStore().is_session_active(state, first_session['session_token'])
    assert SessionStore().is_session_active(state, second_session['session_token'])


def test__session_store__correct_user_returned_from_token(state, session, db_session_1, db_session_2, db_user_1):
    assert SessionStore().get_user_from_session_token(state, db_session_1.token).id == db_user_1.id


def test__session_store__raises_on_invalid_token(state, session):
    with pytest.raises(SessionExpired):
        assert SessionStore().get_user_from_session_token(state, 'invalid token') is None


def test__session_store__two_users_independent_sessions(
    mocker, token_1, token_2, expire_valid, state, session, db_user_1, db_user_2
):
    mocker.patch('secrets.token_urlsafe', side_effect=[token_1, token_2])
    mocker.patch('bw.models.auth.Session.api_session_length', return_value=expire_valid)

    session1 = SessionStore().start_api_session(state, db_user_1)
    session2 = SessionStore().start_api_session(state, db_user_2)

    assert SessionStore().is_session_active(state, session1['session_token'])
    assert SessionStore().is_session_active(state, session2['session_token'])
    assert session1['session_token'] != session2['session_token']


def test__session_store__expiring_one_user_does_not_affect_other(
    mocker, token_1, token_2, expire_valid, state, session, db_user_1, db_user_2
):
    mocker.patch('secrets.token_urlsafe', side_effect=[token_1, token_2])
    mocker.patch('bw.models.auth.Session.api_session_length', return_value=expire_valid)

    session1 = SessionStore().start_api_session(state, db_user_1)
    session2 = SessionStore().start_api_session(state, db_user_2)

    SessionStore().expire_session_from_user(state, db_user_1)
    assert not SessionStore().is_session_active(state, session1['session_token'])
    assert SessionStore().is_session_active(state, session2['session_token'])


def test__session_store__expired_session_replaced_with_new(
    mocker, token_1, expire_invalid, expire_valid, state, session, db_user_1
):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    mocker.patch('bw.models.auth.Session.api_session_length', return_value=expire_invalid)
    SessionStore().start_api_session(state, db_user_1)
    assert not SessionStore().is_session_active(state, token_1)

    mocker.patch('bw.models.auth.Session.api_session_length', return_value=expire_valid)
    new_session = SessionStore().start_api_session(state, db_user_1)
    assert SessionStore().is_session_active(state, new_session['session_token'])


def test__session_store__get_user_from_expired_token_raises(mocker, token_1, expire_invalid, state, session, db_user_1):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    mocker.patch('bw.models.auth.Session.api_session_length', return_value=expire_invalid)
    session_data = SessionStore().start_api_session(state, db_user_1)
    assert not SessionStore().is_session_active(state, session_data['session_token'])
    with pytest.raises(SessionExpired):
        SessionStore().get_user_from_session_token(state, session_data['session_token'])


def test__session_store__register_oauth_code_stores_code(state, session, oauth_code_1, oauth_state_1):
    """Test that OAuth code is successfully stored in database"""
    SessionStore().register_discord_oauth_code(state, oauth_code_1, oauth_state_1)

    # Verify by checking database directly, not by calling get method
    with state.Session.begin() as db_session:
        query = select(DiscordOAuthCode).where(DiscordOAuthCode.state == oauth_state_1)
        result = db_session.execute(query).first()
        assert result is not None
        assert result[0].code == oauth_code_1


def test__session_store__get_oauth_code_deletes_after_retrieval(state, session, db_oauth_code_2, oauth_state_2):
    """Test that OAuth code is deleted after being retrieved once"""
    # First retrieval should work
    retrieved_code = SessionStore().get_discord_oauth_code(state, oauth_state_2)
    assert retrieved_code == db_oauth_code_2.code

    # Second retrieval should fail
    with pytest.raises(NoAccessCodeFound):
        SessionStore().get_discord_oauth_code(state, oauth_state_2)


def test__session_store__get_oauth_code_raises_for_nonexistent_state(state, session):
    """Test that attempting to retrieve a non-existent OAuth code raises an error"""
    with pytest.raises(NoAccessCodeFound):
        SessionStore().get_discord_oauth_code(state, 'nonexistent_state')


def test__session_store__get_oauth_code_raises_for_expired_code(state, session, db_oauth_code_expired, oauth_state_3):
    """Test that expired OAuth codes raise NoAccessCodeFound"""
    with pytest.raises(NoAccessCodeFound):
        SessionStore().get_discord_oauth_code(state, oauth_state_3)


def test__session_store__multiple_oauth_codes_independent(
    state, session, db_oauth_code_1, db_oauth_code_2, oauth_state_1, oauth_state_2
):
    """Test that multiple OAuth codes can be stored and retrieved independently"""
    # Both should be retrievable
    assert SessionStore().get_discord_oauth_code(state, oauth_state_1) == db_oauth_code_1.code
    assert SessionStore().get_discord_oauth_code(state, oauth_state_2) == db_oauth_code_2.code


# Tests for start_user_session (direct tests, not just via start_api_session)


def test__session_store__start_user_session_returns_correct_data(mocker, token_1, expire_valid, state, session, db_user_1):
    """Test that start_user_session returns correct session data"""
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    mocker.patch('bw.models.auth.Session.human_session_length', return_value=expire_valid)

    session_data = SessionStore().start_user_session(state, db_user_1)
    assert session_data['session_token'] == token_1
    assert datetime.fromisoformat(session_data['expire_time']) == datetime.fromisoformat(expire_valid)


def test__session_store__start_user_session_creates_active_session(mocker, token_1, expire_valid, state, session, db_user_1):
    """Test that start_user_session creates an active session"""
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    mocker.patch('bw.models.auth.Session.human_session_length', return_value=expire_valid)

    session_data = SessionStore().start_user_session(state, db_user_1)
    assert SessionStore().is_session_active(state, session_data['session_token'])


def test__session_store__start_user_session_does_not_expire_existing(
    mocker, token_1, token_2, expire_valid, state, session, db_user_1
):
    """Test that start_user_session does NOT expire existing sessions (unlike start_api_session)"""
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    mocker.patch('bw.models.auth.Session.human_session_length', return_value=expire_valid)

    first_session = SessionStore().start_user_session(state, db_user_1)

    mocker.patch('secrets.token_urlsafe', return_value=token_2)
    second_session = SessionStore().start_user_session(state, db_user_1)

    # Both sessions should be active (unlike start_api_session which expires the old one)
    assert SessionStore().is_session_active(state, first_session['session_token'])
    assert SessionStore().is_session_active(state, second_session['session_token'])


def test__session_store__start_user_session_raises_on_failure(mocker, state, session, db_user_1):
    """Test that start_user_session raises SessionExpired if creation fails"""
    # Mock the query to return None, simulating a failure
    mocker.patch('secrets.token_urlsafe', return_value='test_token')

    class MockSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, query):
            return None

        def scalar(self, query):
            return None  # Simulate failure

    def mock_begin():
        return MockSession()

    mocker.patch.object(state.Session, 'begin', mock_begin)

    with pytest.raises(SessionExpired):
        SessionStore().start_user_session(state, db_user_1)
