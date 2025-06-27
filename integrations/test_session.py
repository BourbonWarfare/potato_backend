# ruff: noqa: F811, F401

from datetime import datetime

from bw.auth.session import SessionStore
from integrations.fixtures import (
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
)


def test__session_store__is_session_valid__no_session(state, session):
    assert not SessionStore().is_session_active(state, 'no token')


def test__session_store__is_session_valid__with_session(state, session, db_session_1, token_1):
    assert SessionStore().is_session_active(state, token_1)


def test__session_store__starting_session_return_correct(mocker, token_1, expire_valid, state, session, db_user_1):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    mocker.patch('bw.models.auth.Session.api_session_length', return_value=expire_valid)

    new_session = SessionStore().start_api_session(state, db_user_1)
    assert new_session['status'] == 200
    assert new_session['session_token'] == token_1
    assert new_session['expire_time'] == datetime.fromisoformat(expire_valid)


def test__session_store__starting_session_activates(mocker, token_1, expire_valid, state, session, db_user_1):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    mocker.patch('bw.models.auth.Session.api_session_length', return_value=expire_valid)

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


def test__session_store__returns_none_on_invalid_token(state, session):
    assert SessionStore().get_user_from_session_token(state, 'invalid token') is None
