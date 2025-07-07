# ruff: noqa: F811, F401

import pytest
from datetime import datetime

from integrations.auth.fixtures import (
    state,
    session,
    token_1,
    token_2,
    expire_valid,
    db_expired_session_1,
    db_user_1,
    db_user_2,
    expire_invalid,
    db_session_1,
    db_session_2,
    permission_1,
    permission_2,
    permission_3,
    db_permission_1,
    db_permission_2,
    db_permission_3,
    group_name_1,
    group_name_2,
    group_name_3,
    permission_name_1,
    permission_name_2,
    permission_name_3,
    db_group_1,
    db_group_2,
    db_group_3,
    role_1,
    role_2,
    discord_id_1,
    db_discord_user_1,
    db_bot_user_1,
)
from bw.error import DbError, SessionInvalid, NoUserWithGivenCredentials
from bw.auth.api import AuthApi
from bw.auth.user import UserStore
from bw.auth.group import GroupStore


def test__create_new_user_bot__can_create_and_get_token(mocker, state, session, token_1):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)

    response = AuthApi().create_new_user_bot(state)
    assert response.contained_json['status'] == 201
    assert response.contained_json['bot_token'] == token_1


def test__create_new_user_discord__can_create(mocker, state, session):
    response = AuthApi().create_new_user_from_discord(state, 1)
    assert response.status == '201 CREATED'


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


def test__login_with_discord__can_login_when_generic_expire(mocker, state, session, token_1, expire_valid):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)

    AuthApi().create_new_user_from_discord(state, 1)
    response = AuthApi().login_with_discord(state, 1)
    assert response.contained_json['status'] == 200
    assert response.contained_json['session_token'] == token_1
    assert response.contained_json['status'] == 200
    assert response.contained_json['session_token'] == token_1


def test__login_with_bot__can_login_when_user_exists(mocker, state, session, token_1, expire_valid):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    mocker.patch('bw.models.auth.Session.api_session_length', return_value=expire_valid)

    AuthApi().create_new_user_bot(state)
    response = AuthApi().login_with_bot(state, token_1)
    assert response.contained_json['status'] == 200
    assert response.contained_json['session_token'] == token_1
    assert datetime.fromisoformat(response.contained_json['expire_time']) == datetime.fromisoformat(expire_valid)


def test__login_with_bot__can_login_when_generic_expire(mocker, state, session, token_1, expire_valid):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)

    AuthApi().create_new_user_bot(state)
    response = AuthApi().login_with_bot(state, token_1)
    assert response.contained_json['status'] == 200
    assert response.contained_json['session_token'] == token_1


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


def test__create_new_user_bot__rolls_back_on_error(mocker, state, session):
    mocker.patch('bw.auth.user.UserStore.link_bot_user', side_effect=DbError)
    response = AuthApi().create_new_user_bot(state)
    assert response.contained_json['status'] == 400

    mocker.patch('bw.auth.user.UserStore.link_bot_user', side_effect=NoUserWithGivenCredentials)
    response = AuthApi().create_new_user_bot(state)
    assert response.contained_json['status'] == 404


def test__create_new_user_from_discord__rolls_back_on_error(mocker, state, session):
    mocker.patch('bw.auth.user.UserStore.link_discord_user', side_effect=DbError)
    response = AuthApi().create_new_user_from_discord(state, 1)
    assert response.status_code == 400

    mocker.patch('bw.auth.user.UserStore.link_discord_user', side_effect=NoUserWithGivenCredentials)
    response = AuthApi().create_new_user_from_discord(state, 1)
    assert response.status_code == 404


def test__does_user_have_roles__no_session(state, session, role_1):
    assert not AuthApi().does_user_have_roles(state, 'no-token', role_1)


def test__does_user_have_roles__invalid_session(mocker, state, session, role_1):
    mocker.patch('bw.auth.session.SessionStore.get_user_from_session_token', side_effect=SessionInvalid)
    assert not AuthApi().does_user_have_roles(state, 'some-token', role_1)


def test__does_user_have_roles__no_roles(state, session, db_session_1, token_1, role_1):
    assert not AuthApi().does_user_have_roles(state, token_1, role_1)


def test__does_user_have_roles__has_some_roles(state, session, db_user_1, db_session_1, token_1, role_1, role_2):
    UserStore().create_role(state, 'test_role', role_1)
    UserStore().assign_user_role(state, db_user_1, 'test_role')
    assert not AuthApi().does_user_have_roles(state, token_1, role_2)


def test__does_user_have_roles__has_all_roles(state, session, db_user_1, db_session_1, token_1, role_1):
    UserStore().create_role(state, 'test_role', role_1)
    UserStore().assign_user_role(state, db_user_1, 'test_role')
    assert AuthApi().does_user_have_roles(state, token_1, role_1)


def test__does_user_have_permissions__no_session(state, session, permission_1):
    assert not AuthApi().does_user_have_permissions(state, 'no-token', permission_1)


def test__does_user_have_permissions__invalid_session(mocker, state, session, permission_1):
    mocker.patch('bw.auth.session.SessionStore.get_user_from_session_token', side_effect=SessionInvalid)
    assert not AuthApi().does_user_have_permissions(state, 'some-token', permission_1)


def test__does_user_have_permissions__no_permissions(state, session, db_session_1, token_1, permission_1):
    assert not AuthApi().does_user_have_permissions(state, token_1, permission_1)


def test__does_user_have_permissions__has_some_permissions(
    state, session, db_user_1, db_session_1, token_1, db_group_1, permission_1, permission_2
):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    assert not AuthApi().does_user_have_permissions(state, token_1, permission_2)


def test__does_user_have_permissions__has_all_permissions(
    state, session, db_user_1, db_session_1, token_1, db_group_1, permission_1
):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    assert AuthApi().does_user_have_permissions(state, token_1, permission_1)


def test__does_user_have_permissions__group_has_no_permissions(
    state, session, db_user_1, db_session_1, token_1, db_group_3, permission_1
):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_3)
    assert not AuthApi().does_user_have_permissions(state, token_1, permission_1)


def test__revoke_discord_user_session__no_user(state, session):
    response = AuthApi().revoke_discord_user_session(state, 123)
    assert response.status_code == 404


def test__revoke_bot_user_session__no_user(state, session):
    response = AuthApi().revoke_bot_user_session(state, 'not-a-token')
    assert response.status_code == 404


def test__revoke_discord_user_session__user_exists(state, session, db_discord_user_1, db_session_1):
    response = AuthApi().revoke_discord_user_session(state, db_discord_user_1.discord_id)
    assert response.status_code == 200
    assert not AuthApi().is_session_active(state, db_session_1.token)


def test__revoke_bot_user_session__user_exists(state, session, db_bot_user_1, db_session_1):
    response = AuthApi().revoke_bot_user_session(state, db_bot_user_1.bot_token)
    assert response.status_code == 200
    assert not AuthApi().is_session_active(state, db_session_1.token)
