# ruff: noqa: F811, F401

import pytest
from datetime import datetime

from integrations.auth.fixtures import (
    state,
    session,
    token_1,
    expire_valid,
    db_expired_session_1,
    db_user_1,
    expire_invalid,
    db_session_1,
)
from bw.error import NoUserWithGivenCredentials, DbError
from bw.auth.api import AuthApi


def test__create_new_user_bot__can_create_and_get_token(mocker, state, session, token_1):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)

    response = AuthApi().create_new_user_bot(state)
    assert response.contained_json['status'] == 200
    assert response.contained_json['bot_token'] == token_1


def test__create_new_user_discord__can_create(mocker, state, session):
    response = AuthApi().create_new_user_from_discord(state, 1)
    assert response.status == '200 OK'


def test__login_with_discord__can_login_when_user_exists(mocker, state, session, token_1, expire_valid):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    mocker.patch('bw.models.auth.Session.api_session_length', return_value=expire_valid)

    AuthApi().create_new_user_from_discord(state, 1)
    response = AuthApi().login_with_discord(state, 1)
    assert response.contained_json['status'] == 200
    assert response.contained_json['session_token'] == token_1
    assert datetime.fromisoformat(response.contained_json['expire_time']) == datetime.fromisoformat(expire_valid)


def test__login_with_discord__invalid_id(mocker, state, session, token_1):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)

    response = AuthApi().login_with_discord(state, 1)
    assert response.contained_json['status'] == 404


def test__login_with_bot__can_login_when_user_exists(mocker, state, session, token_1, expire_valid):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    mocker.patch('bw.models.auth.Session.api_session_length', return_value=expire_valid)

    AuthApi().create_new_user_bot(state)
    response = AuthApi().login_with_bot(state, token_1)
    assert response.contained_json['status'] == 200
    assert response.contained_json['session_token'] == token_1
    assert datetime.fromisoformat(response.contained_json['expire_time']) == datetime.fromisoformat(expire_valid)


def test__login_with_bot__invalid_id(mocker, state, session, token_1):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)

    response = AuthApi().login_with_bot(state, token_1)
    assert response.contained_json['status'] == 404


def test__is_session_active__no_session(state, session):
    assert not AuthApi().is_session_active(state, 'no token')


def test__is_session_active__with_session(state, session, db_session_1, token_1, db_user_1):
    assert AuthApi().is_session_active(state, token_1)


def test__is_session_active__with_expired_session(state, session, db_expired_session_1, token_1, db_user_1):
    assert not AuthApi().is_session_active(state, token_1)
