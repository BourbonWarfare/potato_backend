# ruff: noqa: F811, F401

import json
import unittest.mock
import uuid
from datetime import datetime

import aiohttp
import pytest
from quart import Quart

from bw.auth.api import AuthApi
from bw.auth.group import GroupStore
from bw.auth.user import UserStore
from bw.error import (
    CannotDetermineSession,
    DbError,
    GroupAssignmentFailed,
    GroupCreationFailed,
    GroupPermissionCreationFailed,
    NoUserWithGivenCredentials,
    RoleCreationFailed,
    SessionExpired,
)
from bw.models.auth import BourbonUser
from integrations.auth.fixtures import (
    db_bot_user_1,
    db_bourbon_code_1,
    db_bourbon_user_1,
    db_discord_user_1,
    db_expired_session_1,
    db_group_1,
    db_group_2,
    db_group_3,
    db_oauth_code_1,
    db_permission_1,
    db_permission_2,
    db_permission_3,
    db_role_1,
    db_role_2,
    db_session_1,
    db_session_2,
    db_unauthenticated_session_1,
    db_unverified_bourbon_user,
    db_user_1,
    db_user_2,
    discord_id_1,
    email_1,
    email_2,
    expire_invalid,
    expire_valid,
    group_name_1,
    group_name_2,
    group_name_3,
    oauth_code_1,
    oauth_state_1,
    password_1,
    permission_1,
    permission_2,
    permission_3,
    permission_name_1,
    permission_name_2,
    permission_name_3,
    role_1,
    role_2,
    role_name_1,
    role_name_2,
    salt_1,
    token_1,
    token_2,
    username_1,
    username_2,
)
from integrations.fixtures import test_app


class TestAuthApiSessionCookie:
    def test__get_session_cookie__raises_when_no_request_context(self):
        with pytest.raises(CannotDetermineSession):
            AuthApi().get_session_cookie()

    @pytest.mark.asyncio
    async def test__get_session_cookie__raises_when_session_key_missing(self, test_app):
        async with test_app.app.test_request_context('/'):
            with pytest.raises(CannotDetermineSession):
                AuthApi().get_session_cookie()

    @pytest.mark.asyncio
    async def test__store_and_get_session_cookie__success(self, test_app, token_1):
        async with test_app.app.test_request_context('/'):
            AuthApi().store_session_cookie(token_1)
            assert AuthApi().get_session_cookie() == token_1


class TestAuthApiBot:
    def test__create_new_user_bot__can_create_and_get_token(self, mocker, state, token_1):
        mocker.patch('secrets.token_urlsafe', return_value=token_1)

        response = AuthApi().create_new_user_bot(state)
        assert response.status_code == 201
        assert response.contained_json['bot_token'] == token_1

    def test__create_new_user_bot__rolls_back_on_error(self, mocker, state, session):
        mocker.patch('bw.auth.user.UserStore.link_bot_user', side_effect=DbError)
        response = AuthApi().create_new_user_bot(state)
        assert response.status_code == 400

        mocker.patch('bw.auth.user.UserStore.link_bot_user', side_effect=NoUserWithGivenCredentials)
        response = AuthApi().create_new_user_bot(state)
        assert response.status_code == 404

    def test__login_with_bot__can_login_when_user_exists(self, mocker, state, token_1, expire_valid):
        mocker.patch('secrets.token_urlsafe', return_value=token_1)
        mocker.patch('bw.models.auth.Session.api_session_length', return_value=expire_valid)

        AuthApi().create_new_user_bot(state)
        response = AuthApi().login_with_bot(state, token_1)
        assert response.status_code == 200
        assert response.contained_json['session_token'] == token_1
        assert datetime.fromisoformat(response.contained_json['expire_time']) == datetime.fromisoformat(expire_valid)

    def test__login_with_bot__can_login_when_generic_expire(self, mocker, state, token_1, expire_valid):
        mocker.patch('secrets.token_urlsafe', return_value=token_1)

        AuthApi().create_new_user_bot(state)
        response = AuthApi().login_with_bot(state, token_1)
        assert response.status_code == 200
        assert response.contained_json['session_token'] == token_1

    def test__login_with_bot__invalid_id(self, mocker, state, token_1):
        mocker.patch('secrets.token_urlsafe', return_value=token_1)

        response = AuthApi().login_with_bot(state, token_1)
        assert response.status_code == 404

    def test__revoke_bot_user_session__no_user(self, state, token_1):
        response = AuthApi().revoke_bot_user_session(state, token_1)
        assert response.status_code == 404

    def test__revoke_bot_user_session__user_exists(self, state, db_bot_user_1, db_session_1):
        response = AuthApi().revoke_bot_user_session(state, db_bot_user_1.bot_token)
        assert response.status_code == 200
        assert not AuthApi().is_session_active(state, db_session_1.token)


class TestAuthApiDiscord:
    @pytest.mark.asyncio
    async def test__login_with_discord__can_login_when_user_exists(
        self, mocker, state, token_1, token_2, expire_valid, discord_id_1, db_discord_user_1
    ):
        class MockSessionObject:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args, **_kwargs):
                pass

            def raise_for_status(self):
                pass

            async def json(self) -> dict:
                return {'id': db_discord_user_1.discord_id}

        mocker.patch('secrets.token_urlsafe', return_value=token_1)
        mocker.patch('bw.models.auth.Session.human_session_length', return_value=expire_valid)
        mocker.patch('bw.auth.api.ENVIRONMENT.discord_api_url', return_value='https://example.com')
        mocker.patch('bw.auth.api.aiohttp.ClientSession.get', return_value=MockSessionObject())

        response = await AuthApi().login_with_discord(state, token_2)
        assert response.status_code == 200
        assert response.contained_json['session_token'] == token_1
        assert datetime.fromisoformat(response.contained_json['expire_time']) == datetime.fromisoformat(expire_valid)

    @pytest.mark.asyncio
    async def test__login_with_discord__nonexistant_id_creates_user(
        self, mocker, state, expire_valid, token_1, token_2, discord_id_1
    ):
        class MockSessionObject:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args, **_kwargs):
                pass

            def raise_for_status(self):
                pass

            async def json(self) -> dict:
                return {'id': discord_id_1}

        mocker.patch('secrets.token_urlsafe', return_value=token_1)
        mocker.patch('bw.models.auth.Session.human_session_length', return_value=expire_valid)
        mocker.patch('bw.auth.api.ENVIRONMENT.discord_api_url', return_value='https://example.com')
        mocker.patch('bw.auth.api.aiohttp.ClientSession.get', return_value=MockSessionObject())

        response = await AuthApi().login_with_discord(state, token_2)
        assert response.status_code == 200
        assert response.contained_json['session_token'] == token_1
        assert datetime.fromisoformat(response.contained_json['expire_time']) == datetime.fromisoformat(expire_valid)

    @pytest.mark.asyncio
    async def test__login_with_discord__bad_token_fails(self, mocker, state, token_1, token_2, db_discord_user_1):
        class MockSessionObject:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args, **_kwargs):
                pass

            def raise_for_status(self):
                raise aiohttp.ClientResponseError(None, None, status=401, message='bad')

            async def json(self) -> dict:
                return {'id': db_discord_user_1.discord_id}

        mocker.patch('secrets.token_urlsafe', return_value=token_1)
        mocker.patch('bw.models.auth.Session.human_session_length', return_value=expire_valid)
        mocker.patch('bw.auth.api.ENVIRONMENT.discord_api_url', return_value='https://example.com')
        mocker.patch('bw.auth.api.aiohttp.ClientSession.get', return_value=MockSessionObject())

        response = await AuthApi().login_with_discord(state, token_2)
        assert response.status_code == 401

    def test__revoke_discord_user_session__no_user(self, state, discord_id_1):
        response = AuthApi().revoke_discord_user_session(state, discord_id_1)
        assert response.status_code == 404

    def test__revoke_discord_user_session__user_exists(self, state, db_discord_user_1, db_session_1):
        response = AuthApi().revoke_discord_user_session(state, db_discord_user_1.discord_id)
        assert response.status_code == 200
        assert not AuthApi().is_session_active(state, db_session_1.token)


class TestAuthApiSession:
    def test__is_session_active__no_session(self, state, session):
        assert not AuthApi().is_session_active(state, 'no token')

    def test__is_session_active__with_session(self, state, db_session_1, token_1, db_user_1):
        assert AuthApi().is_session_active(state, token_1)

    def test__is_session_active__with_expired_session(self, state, db_expired_session_1, token_1, db_user_1):
        assert not AuthApi().is_session_active(state, token_1)

    def test__is_session_authenticated__true_for_authenticated_session(self, state, db_session_1, token_1):
        assert AuthApi().is_session_authenticated(state, token_1)

    def test__is_session_authenticated__false_for_unauthenticated_session(self, state, db_unauthenticated_session_1, token_1):
        assert not AuthApi().is_session_authenticated(state, token_1)

    def test__is_session_authenticated__false_for_nonexistent_session(self, state):
        assert not AuthApi().is_session_authenticated(state, 'nonexistent_token')

    def test__set_csrf_token__token_set_for_session(self, state, db_unauthenticated_session_1, token_1):
        with unittest.mock.patch('bw.auth.api.secure_token_urlsafe', return_value=token_1):
            response = AuthApi().set_csrf_token(state, db_unauthenticated_session_1.token)
        assert response.status == '200 OK'
        assert response.state == token_1

    def test__set_csrf_token__token_not_set_for_invalid_session(self, state, token_1):
        with unittest.mock.patch('bw.auth.api.secure_token_urlsafe', return_value=token_1):
            response = AuthApi().set_csrf_token(state, 'blah')

        assert response.status == '200 OK'
        assert response.state == token_1


class TestAuthApiBourbon:
    def test__create_new_user_bourbon__disallowed_password_chars_returns_bad_request(self, state, email_1, username_1):
        response = AuthApi().create_new_user_bourbon(state, username_1, email_1, 'password😀')
        assert response.status_code == 400

    def test__create_new_user_bourbon__success(self, mocker, state, email_1, username_1, password_1):
        mocker.patch('bw.auth.api.ENVIRONMENT.verify_immediately', return_value=True)
        response = AuthApi().create_new_user_bourbon(state, username_1, email_1, password_1)
        assert response.status_code == 201

    def test__create_new_user_bourbon__duplicate_user_rolls_back_and_fails(self, mocker, state, db_bourbon_user_1, password_1):
        mocker.patch('bw.auth.api.ENVIRONMENT.verify_immediately', return_value=True)
        response = AuthApi().create_new_user_bourbon(state, db_bourbon_user_1.username, db_bourbon_user_1.email, password_1)
        assert response.status_code in (400, 409)

    def test__login_with_bourbon__success_via_username(self, state, db_bourbon_user_1, username_1, password_1):
        response = AuthApi().login_with_bourbon(state, username_1, password_1, redirect='/dashboard')
        assert response.status_code == 200
        assert response.headers['Location'] == '/dashboard'
        assert response.headers['HX-Redirect'] == '/dashboard'
        assert AuthApi().is_session_authenticated(state, response.state['session_token'])

    def test__login_with_bourbon__success_via_email(self, state, db_bourbon_user_1, email_1, password_1):
        response = AuthApi().login_with_bourbon(state, email_1, password_1, redirect='/home')
        assert response.status_code == 200
        assert response.headers['Location'] == '/home'
        assert AuthApi().is_session_authenticated(state, response.state['session_token'])

    def test__login_with_bourbon__unverified_user_creates_unauthenticated_session(
        self, state, db_unverified_bourbon_user, username_2, password_1
    ):
        response = AuthApi().login_with_bourbon(state, username_2, password_1, redirect='/home')
        assert response.status_code == 200
        assert not AuthApi().is_session_authenticated(state, response.state['session_token'])

    def test__login_with_bourbon__nonexistent_user_returns_404(self, state):
        response = AuthApi().login_with_bourbon(state, 'nonexistent_user', 'password123', redirect='/')
        assert response.status_code == 404

    def test__login_with_bourbon__invalid_password_returns_401(self, state, db_bourbon_user_1, username_1):
        response = AuthApi().login_with_bourbon(state, username_1, 'wrong_password', redirect='/')
        assert response.status_code == 401


class TestAuthApiEmailVerification:
    def test__send_verification_email__verify_immediately_true(self, mocker, state, email_1):
        mocker.patch('bw.auth.api.ENVIRONMENT.verify_immediately', return_value=True)
        response = AuthApi().send_verification_email(state, email_1)
        assert response.status_code == 201

    def test__send_verification_email__verify_immediately_false_enqueues_task(self, mocker, state, email_1, token_1):
        mocker.patch('bw.auth.api.ENVIRONMENT.verify_immediately', return_value=False)
        mocker.patch('secrets.token_urlsafe', return_value=token_1)
        mock_enqueue = mocker.patch('bw.tasks.tasks.TasksStore.enqueue_task')

        response = AuthApi().send_verification_email(state, email_1)
        assert response.status_code == 201
        mock_enqueue.assert_called_once()

    def test__verify_email__success_with_valid_token(self, state, db_bourbon_user_1, db_bourbon_code_1):
        response = AuthApi().verify_email(state, db_bourbon_code_1.code)
        assert response.status_code == 200

    def test__verify_email__invalid_token_returns_forbidden(self, state):
        response = AuthApi().verify_email(state, 'invalid_authorization_token')
        assert response.status_code == 403


class TestAuthApiOAuthCode:
    def test__register_access_code__success(self, state, oauth_code_1, oauth_state_1):
        response = AuthApi().register_access_code(state, oauth_code_1, oauth_state_1)
        assert response.status_code == 200

    def test__retrieve_access_code__success(self, state, db_oauth_code_1, oauth_code_1, oauth_state_1):
        response = AuthApi().retrieve_access_code(state, oauth_state_1)
        assert response.status_code == 200
        assert response.contained_json['access_code'] == oauth_code_1

    def test__retrieve_access_code__nonexistent_state_returns_404(self, state):
        response = AuthApi().retrieve_access_code(state, 'nonexistent_oauth_state')
        assert response.status_code == 404


class TestAuthApiRoles:
    def test__does_user_have_roles__no_session(self, state, role_1):
        assert not AuthApi().does_user_have_roles(state, 'no-token', role_1)

    def test__does_user_have_roles__invalid_session(self, mocker, state, role_1):
        mocker.patch('bw.auth.session.SessionStore.get_user_from_session_token', side_effect=SessionExpired)
        assert not AuthApi().does_user_have_roles(state, 'some-token', role_1)

    def test__does_user_have_roles__no_roles(self, state, db_session_1, token_1, role_1):
        assert not AuthApi().does_user_have_roles(state, token_1, role_1)

    def test__does_user_have_roles__has_some_roles(self, state, db_user_1, db_session_1, token_1, role_1, role_2, role_name_1):
        UserStore().create_role(state, role_name_1, role_1)
        UserStore().assign_user_role(state, db_user_1, role_name_1)
        assert not AuthApi().does_user_have_roles(state, token_1, role_2)

    def test__does_user_have_roles__has_all_roles(self, state, db_user_1, db_session_1, token_1, role_1, role_name_1):
        UserStore().create_role(state, role_name_1, role_1)
        UserStore().assign_user_role(state, db_user_1, role_name_1)
        assert AuthApi().does_user_have_roles(state, token_1, role_1)

    def test__create_role__success(self, state, role_1, role_name_1):
        response = AuthApi().create_role(state, role_name_1, role_1)
        assert response.status_code == 201
        assert response.contained_json['name'] == role_name_1

    def test__create_role__failure(self, mocker, state, role_1, role_name_1):
        mocker.patch('bw.auth.user.UserStore.create_role', side_effect=RoleCreationFailed(role_name_1))
        response = AuthApi().create_role(state, role_name_1, role_1)
        assert response.status_code == 409

    def test__assign_role__success(self, state, db_user_1, role_1, role_name_1):
        UserStore().create_role(state, role_name_1, role_1)
        response = AuthApi().assign_role(state, role_name_1, db_user_1.uuid)
        assert response.status_code == 200

    def test__assign_role__no_user(self, state, role_1, role_name_1):
        UserStore().create_role(state, role_name_1, role_1)
        fake_uuid = uuid.uuid4()
        response = AuthApi().assign_role(state, role_name_1, fake_uuid)
        assert response.status_code == 404

    def test__assign_role__no_role(self, state, db_user_1):
        response = AuthApi().assign_role(state, 'nonexistent_role', db_user_1.uuid)
        assert response.status_code == 404

    def test__get_all_roles__empty_database_returns_empty_json(self, state, session):
        response = AuthApi().get_all_roles(state)
        assert response.status_code == 200
        assert response.contained_json['roles'] == []

    def test__get_all_roles__single_role_returns_correctly(self, state, db_role_1, role_name_1, role_1):
        response = AuthApi().get_all_roles(state)
        assert response.status_code == 200
        assert len(response.contained_json['roles']) == 1

        role = response.contained_json['roles'][0]
        assert role['name'] == role_name_1
        assert role == {'name': role_name_1, **role_1.as_dict()}

    def test__get_all_roles__multiple_roles_returns_all(
        self, state, db_role_1, db_role_2, role_name_1, role_name_2, role_1, role_2
    ):
        response = AuthApi().get_all_roles(state)
        assert response.status_code == 200
        assert len(response.contained_json['roles']) == 2

        role_names = {role['name'] for role in response.contained_json['roles']}
        assert role_names == {role_name_1, role_name_2}

    def test__get_all_roles__role_permissions_included(self, state, db_role_1, role_1):
        response = AuthApi().get_all_roles(state)
        role = response.contained_json['roles'][0]

        for key, value in role_1.as_dict().items():
            assert role[key] == value

    def test__delete_role__success_returns_ok(self, state, db_role_1, role_name_1):
        response = AuthApi().delete_role(state, role_name_1)
        assert response.status_code == 200

    def test__delete_role__actually_deletes_role(self, state, db_role_1, role_name_1):
        AuthApi().delete_role(state, role_name_1)
        roles = UserStore().get_all_roles(state)
        assert len(roles) == 0

    def test__delete_role__nonexistent_role_returns_error(self, state, session):
        response = AuthApi().delete_role(state, 'nonexistent_role')
        assert response.status_code == 404

    def test__delete_role__removes_from_users(self, state, db_role_1, db_user_1, role_name_1):
        UserStore().assign_user_role(state, db_user_1, role_name_1)
        AuthApi().delete_role(state, role_name_1)

        user_role = UserStore().get_users_role(state, db_user_1)
        assert user_role is None

    def test__delete_role__does_not_affect_other_roles(self, state, db_role_1, db_role_2, role_name_1):
        AuthApi().delete_role(state, role_name_1)

        roles = UserStore().get_all_roles(state)
        assert len(roles) == 1
        assert roles[0].id == db_role_2.id

    def test__edit_role__success_returns_json_with_name(self, state, db_role_1, role_name_1, role_2):
        response = AuthApi().edit_role(state, role_name_1, role_2)
        assert response.status_code == 200
        assert response.contained_json['name'] == role_name_1

    def test__edit_role__actually_updates_role(self, state, db_role_1, role_name_1, role_1, role_2):
        AuthApi().edit_role(state, role_name_1, role_2)

        roles = UserStore().get_all_roles(state)
        updated_role = roles[0]
        assert updated_role.into_roles().as_dict() == role_2.as_dict()
        assert updated_role.into_roles().as_dict() != role_1.as_dict()

    def test__edit_role__nonexistent_role_returns_error(self, state, role_1):
        response = AuthApi().edit_role(state, 'nonexistent_role', role_1)
        assert response.status_code == 404

    def test__edit_role__keeps_same_id(self, state, db_role_1, role_name_1, role_2):
        original_id = db_role_1.id
        AuthApi().edit_role(state, role_name_1, role_2)

        roles = UserStore().get_all_roles(state)
        assert roles[0].id == original_id

    def test__edit_role__does_not_affect_other_roles(self, state, db_role_1, db_role_2, role_name_1, role_2):
        original_role_2_data = db_role_2.into_roles().as_dict()
        AuthApi().edit_role(state, role_name_1, role_2)

        roles = UserStore().get_all_roles(state)
        role_2_after = next(r for r in roles if r.id == db_role_2.id)
        assert role_2_after.into_roles().as_dict() == original_role_2_data


class TestAuthApiPermissions:
    def test__does_user_have_permissions__no_session(self, state, permission_1):
        assert not AuthApi().does_user_have_permissions(state, 'no-token', permission_1)

    def test__does_user_have_permissions__invalid_session(self, mocker, state, permission_1):
        mocker.patch('bw.auth.session.SessionStore.get_user_from_session_token', side_effect=SessionExpired)
        assert not AuthApi().does_user_have_permissions(state, 'some-token', permission_1)

    def test__does_user_have_permissions__no_permissions(self, state, db_session_1, token_1, permission_1):
        assert not AuthApi().does_user_have_permissions(state, token_1, permission_1)

    def test__does_user_have_permissions__has_some_permissions(
        self, state, db_user_1, db_session_1, token_1, db_group_1, permission_1, permission_2
    ):
        GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
        assert not AuthApi().does_user_have_permissions(state, token_1, permission_2)

    def test__does_user_have_permissions__has_all_permissions(
        self, state, db_user_1, db_session_1, token_1, db_group_1, permission_1
    ):
        GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
        assert AuthApi().does_user_have_permissions(state, token_1, permission_1)

    def test__does_user_have_permissions__group_has_no_permissions(
        self, state, db_user_1, db_session_1, token_1, db_group_3, permission_1
    ):
        GroupStore().assign_user_to_group(state, db_user_1, db_group_3)
        assert not AuthApi().does_user_have_permissions(state, token_1, permission_1)

    def test__create_group_permission__success(self, state, permission_1, permission_name_1):
        response = AuthApi().create_group_permission(state, permission_name_1, permission_1)
        assert response.status_code == 201
        assert response.contained_json['name'] == permission_name_1

    def test__create_group_permission__failure(self, mocker, state, permission_1, permission_name_1):
        mocker.patch('bw.auth.group.GroupStore.create_permission', side_effect=GroupPermissionCreationFailed(permission_name_1))
        response = AuthApi().create_group_permission(state, permission_name_1, permission_1)
        assert response.status_code == 409

    def test__get_all_permissions__empty_database_returns_empty_json(self, state, session):
        response = AuthApi().get_all_permissions(state)
        assert response.status_code == 200
        assert response.contained_json['permissions'] == []

    def test__get_all_permissions__single_permission_returns_correctly(
        self, state, db_permission_1, permission_name_1, permission_1
    ):
        response = AuthApi().get_all_permissions(state)
        assert response.status_code == 200
        assert len(response.contained_json['permissions']) == 1

        perm = response.contained_json['permissions'][0]
        assert perm['name'] == permission_name_1
        assert perm == {'name': permission_name_1, **permission_1.as_dict()}

    def test__get_all_permissions__multiple_permissions_returns_all(
        self, state, db_permission_1, db_permission_2, db_permission_3
    ):
        response = AuthApi().get_all_permissions(state)
        assert response.status_code == 200
        assert len(response.contained_json['permissions']) == 3

        perm_names = {perm['name'] for perm in response.contained_json['permissions']}
        assert perm_names == {db_permission_1.name, db_permission_2.name, db_permission_3.name}

    def test__get_all_permissions__permission_grants_included(self, state, db_permission_1, permission_1):
        response = AuthApi().get_all_permissions(state)
        perm = response.contained_json['permissions'][0]

        for key, value in permission_1.as_dict().items():
            assert perm[key] == value

    def test__delete_permission__success_returns_ok(self, state, db_permission_1, permission_name_1):
        response = AuthApi().delete_permission(state, permission_name_1)
        assert response.status_code == 200

    def test__delete_permission__actually_deletes_permission(self, state, db_permission_1, permission_name_1):
        AuthApi().delete_permission(state, permission_name_1)

        permissions = GroupStore().get_all_permissions(state)
        assert len(permissions) == 0

    def test__delete_permission__nonexistent_permission_returns_error(self, state, session):
        response = AuthApi().delete_permission(state, 'nonexistent_permission')
        assert response.status_code == 404

    def test__delete_permission__does_not_affect_other_permissions(
        self, state, db_permission_1, db_permission_2, permission_name_1
    ):
        AuthApi().delete_permission(state, permission_name_1)

        permissions = GroupStore().get_all_permissions(state)
        assert len(permissions) == 1
        assert permissions[0].id == db_permission_2.id

    def test__edit_permission__success_returns_json_with_name(self, state, db_permission_1, permission_name_1, permission_2):
        response = AuthApi().edit_permission(state, permission_name_1, permission_2)
        assert response.status_code == 200
        assert response.contained_json['name'] == permission_name_1

    def test__edit_permission__actually_updates_permission(
        self, state, db_permission_1, permission_name_1, permission_1, permission_2
    ):
        AuthApi().edit_permission(state, permission_name_1, permission_2)

        permissions = GroupStore().get_all_permissions(state)
        updated_perm = permissions[0]
        assert updated_perm.into_permissions().as_dict() == permission_2.as_dict()
        assert updated_perm.into_permissions().as_dict() != permission_1.as_dict()

    def test__edit_permission__nonexistent_permission_returns_error(self, state, permission_1):
        response = AuthApi().edit_permission(state, 'nonexistent_permission', permission_1)
        assert response.status_code == 404

    def test__edit_permission__keeps_same_id(self, state, db_permission_1, permission_name_1, permission_2):
        original_id = db_permission_1.id
        AuthApi().edit_permission(state, permission_name_1, permission_2)

        permissions = GroupStore().get_all_permissions(state)
        assert permissions[0].id == original_id

    def test__edit_permission__does_not_affect_other_permissions(
        self, state, db_permission_1, db_permission_2, permission_name_1, permission_2
    ):
        original_perm_2_data = db_permission_2.into_permissions().as_dict()
        AuthApi().edit_permission(state, permission_name_1, permission_2)

        permissions = GroupStore().get_all_permissions(state)
        perm_2_after = next(p for p in permissions if p.id == db_permission_2.id)
        assert perm_2_after.into_permissions().as_dict() == original_perm_2_data

    def test__edit_permission__groups_using_permission_get_updated_permissions(
        self, state, db_group_1, db_user_1, db_permission_1, permission_name_1, permission_1, permission_2
    ):
        GroupStore().assign_user_to_group(state, db_user_1, db_group_1)

        perms_before = GroupStore().get_all_permissions_user_has(state, db_user_1)
        assert perms_before.as_dict() == permission_1.as_dict()

        AuthApi().edit_permission(state, permission_name_1, permission_2)

        perms_after = GroupStore().get_all_permissions_user_has(state, db_user_1)
        assert perms_after.as_dict() == permission_2.as_dict()


class TestAuthApiGroups:
    def test__create_group__success(self, state, db_permission_1, group_name_1):
        response = AuthApi().create_group(state, group_name_1, db_permission_1.name)
        assert response.status_code == 201
        assert response.contained_json['name'] == group_name_1

    def test__create_group__failure(self, mocker, state, db_permission_1, group_name_1):
        mocker.patch('bw.auth.group.GroupStore.create_group', side_effect=GroupCreationFailed(group_name_1))
        response = AuthApi().create_group(state, group_name_1, db_permission_1.name)
        assert response.status_code == 409

    def test__join_group__success(self, state, db_user_1, db_group_1):
        response = AuthApi().join_group(state, db_user_1, db_group_1.name)
        assert response.status_code == 200

    def test__join_group__no_group(self, state, db_user_1):
        response = AuthApi().join_group(state, db_user_1, 'nonexistent_group')
        assert response.status_code == 404

    def test__join_group__assignment_failed(self, mocker, state, db_user_1, db_group_1):
        mocker.patch('bw.auth.group.GroupStore.assign_user_to_group', side_effect=GroupAssignmentFailed())
        response = AuthApi().join_group(state, db_user_1, db_group_1.name)
        assert response.status_code == 409

    def test__leave_group__success(self, state, db_user_1, db_group_1):
        GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
        response = AuthApi().leave_group(state, db_user_1, db_group_1.name)
        assert response.status_code == 200

    def test__leave_group__no_group(self, state, db_user_1):
        response = AuthApi().leave_group(state, db_user_1, 'nonexistent_group')
        assert response.status_code == 404

    def test__get_all_groups__empty_database_returns_empty_json(self, state, session):
        response = AuthApi().get_all_groups(state)
        assert response.status_code == 200
        assert response.contained_json['groups'] == []

    def test__get_all_groups__single_group_returns_correctly(self, state, db_group_1, group_name_1):
        response = AuthApi().get_all_groups(state)
        assert response.status_code == 200
        assert len(response.contained_json['groups']) == 1

        group = response.contained_json['groups'][0]
        assert group['id'] == db_group_1.id
        assert group['name'] == group_name_1
        assert group['permissions'] == db_group_1.permissions

    def test__get_all_groups__multiple_groups_returns_all(self, state, db_group_1, db_group_2, db_group_3):
        response = AuthApi().get_all_groups(state)
        assert response.status_code == 200
        assert len(response.contained_json['groups']) == 3

        group_ids = {group['id'] for group in response.contained_json['groups']}
        assert group_ids == {db_group_1.id, db_group_2.id, db_group_3.id}

    def test__get_all_groups__group_permission_id_included(self, state, db_group_1, db_permission_1):
        response = AuthApi().get_all_groups(state)
        group = response.contained_json['groups'][0]
        assert group['permissions'] == db_permission_1.id

    def test__delete_group__success_returns_ok(self, state, db_group_1, group_name_1):
        response = AuthApi().delete_group(state, group_name_1)
        assert response.status_code == 200

    def test__delete_group__actually_deletes_group(self, state, db_group_1, group_name_1):
        AuthApi().delete_group(state, group_name_1)

        groups = GroupStore().get_all_groups(state)
        assert len(groups) == 0

    def test__delete_group__nonexistent_group_succeeds(self, state, session):
        response = AuthApi().delete_group(state, 'nonexistent_group')
        assert response.status_code == 200

    def test__delete_group__removes_user_associations(self, state, db_group_1, db_user_1, group_name_1):
        GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
        AuthApi().delete_group(state, group_name_1)

        groups = GroupStore().get_user_groups(state, db_user_1)
        assert len(groups) == 0

    def test__delete_group__does_not_affect_other_groups(self, state, db_group_1, db_group_2, group_name_1):
        AuthApi().delete_group(state, group_name_1)

        groups = GroupStore().get_all_groups(state)
        assert len(groups) == 1
        assert groups[0].id == db_group_2.id


class TestAuthApiUsers:
    def test__auth_api__user_info_returns_uuid(self, state, db_user_1):
        response = AuthApi().user_info(state, db_user_1)
        assert response.status_code == 200
        assert response.contained_json['uuid'] == str(db_user_1.uuid)

    def test__auth_api__user_info_returns_creation_date(self, state, db_user_1):
        response = AuthApi().user_info(state, db_user_1)
        assert response.status_code == 200
        assert response.contained_json['creation_date'] == db_user_1.creation_date.isoformat()

    def test__auth_api__user_info_returns_empty_groups_when_no_memberships(self, state, db_user_1):
        response = AuthApi().user_info(state, db_user_1)
        assert response.status_code == 200
        assert response.contained_json['groups'] == []

    def test__auth_api__user_info_returns_all_groups(self, state, db_user_1, db_group_1, db_group_2):
        GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
        GroupStore().assign_user_to_group(state, db_user_1, db_group_2)

        response = AuthApi().user_info(state, db_user_1)
        assert response.status_code == 200
        assert set(response.contained_json['groups']) == {db_group_1.name, db_group_2.name}

    def test__auth_api__user_info_returns_correct_group_order(self, state, db_user_1, db_group_1, db_group_2):
        GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
        GroupStore().assign_user_to_group(state, db_user_1, db_group_2)

        response = AuthApi().user_info(state, db_user_1)
        assert response.status_code == 200
        groups = response.contained_json['groups']
        assert len(groups) == 2
        assert db_group_1.name in groups
        assert db_group_2.name in groups

    def test__auth_api__user_info_different_users_different_data(self, state, db_user_1, db_user_2, db_group_1):
        GroupStore().assign_user_to_group(state, db_user_1, db_group_1)

        response1 = AuthApi().user_info(state, db_user_1)
        response2 = AuthApi().user_info(state, db_user_2)

        assert response1.contained_json['uuid'] != response2.contained_json['uuid']
        assert len(response1.contained_json['groups']) == 1
        assert len(response2.contained_json['groups']) == 0

    def test__list_all_users__empty_database_returns_empty_json(self, state, session):
        response = AuthApi().list_all_users(state, page=1, page_size=50)
        assert response.status_code == 200
        assert response.contained_json['users'] == []
        assert response.contained_json['total'] == 0
        assert response.contained_json['page'] == 1
        assert response.contained_json['page_size'] == 50
        assert response.contained_json['total_pages'] == 0

    def test__list_all_users__single_user_returns_correct_structure(self, state, db_user_1):
        response = AuthApi().list_all_users(state, page=1, page_size=50)
        assert response.status_code == 200
        assert response.contained_json['total'] == 1
        assert len(response.contained_json['users']) == 1

        user_data = response.contained_json['users'][0]
        assert user_data['uuid'] == str(db_user_1.uuid)

    def test__list_all_users__pagination(self, state, db_user_1, db_user_2):
        response = AuthApi().list_all_users(state, page=1, page_size=1)
        assert response.status_code == 200
        assert response.contained_json['total'] == 2
        assert len(response.contained_json['users']) == 1
        assert response.contained_json['page'] == 1
        assert response.contained_json['page_size'] == 1
        assert response.contained_json['total_pages'] == 2
