# ruff: noqa: F811, F401

import pytest
import uuid
import json
import aiohttp
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
    db_role_1,
    db_role_2,
    role_1,
    role_2,
    role_name_1,
    role_name_2,
    discord_id_1,
    db_discord_user_1,
    db_bot_user_1,
)
from bw.error import (
    DbError,
    SessionExpired,
    NoUserWithGivenCredentials,
    RoleCreationFailed,
    GroupPermissionCreationFailed,
    GroupCreationFailed,
    GroupAssignmentFailed,
)
from bw.auth.api import AuthApi
from bw.auth.user import UserStore
from bw.auth.group import GroupStore


def test__create_new_user_bot__can_create_and_get_token(mocker, state, session, token_1):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)

    response = AuthApi().create_new_user_bot(state)
    assert response.status_code == 201
    assert response.contained_json['bot_token'] == token_1


@pytest.mark.asyncio
async def test__login_with_discord__can_login_when_user_exists(
    mocker, state, session, token_1, token_2, expire_valid, discord_id_1, db_discord_user_1
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
async def test__login_with_discord__nonexistant_id_creates_user(mocker, state, expire_valid, token_1, token_2, discord_id_1):
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
async def test__login_with_discord__bad_token_fails(mocker, state, session, token_1, token_2, db_discord_user_1):
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


def test__login_with_bot__can_login_when_user_exists(mocker, state, session, token_1, expire_valid):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    mocker.patch('bw.models.auth.Session.api_session_length', return_value=expire_valid)

    AuthApi().create_new_user_bot(state)
    response = AuthApi().login_with_bot(state, token_1)
    assert response.status_code == 200
    assert response.contained_json['session_token'] == token_1
    assert datetime.fromisoformat(response.contained_json['expire_time']) == datetime.fromisoformat(expire_valid)


def test__login_with_bot__can_login_when_generic_expire(mocker, state, session, token_1, expire_valid):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)

    AuthApi().create_new_user_bot(state)
    response = AuthApi().login_with_bot(state, token_1)
    assert response.status_code == 200
    assert response.contained_json['session_token'] == token_1


def test__login_with_bot__invalid_id(mocker, state, session, token_1):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)

    response = AuthApi().login_with_bot(state, token_1)
    assert response.status_code == 404


def test__is_session_active__no_session(state, session):
    assert not AuthApi().is_session_active(state, 'no token')


def test__is_session_active__with_session(state, session, db_session_1, token_1, db_user_1):
    assert AuthApi().is_session_active(state, token_1)


def test__is_session_active__with_expired_session(state, session, db_expired_session_1, token_1, db_user_1):
    assert not AuthApi().is_session_active(state, token_1)


def test__create_new_user_bot__rolls_back_on_error(mocker, state, session):
    mocker.patch('bw.auth.user.UserStore.link_bot_user', side_effect=DbError)
    response = AuthApi().create_new_user_bot(state)
    assert response.status_code == 400

    mocker.patch('bw.auth.user.UserStore.link_bot_user', side_effect=NoUserWithGivenCredentials)
    response = AuthApi().create_new_user_bot(state)
    assert response.status_code == 404


def test__does_user_have_roles__no_session(state, session, role_1):
    assert not AuthApi().does_user_have_roles(state, 'no-token', role_1)


def test__does_user_have_roles__invalid_session(mocker, state, session, role_1):
    mocker.patch('bw.auth.session.SessionStore.get_user_from_session_token', side_effect=SessionExpired)
    assert not AuthApi().does_user_have_roles(state, 'some-token', role_1)


def test__does_user_have_roles__no_roles(state, session, db_session_1, token_1, role_1):
    assert not AuthApi().does_user_have_roles(state, token_1, role_1)


def test__does_user_have_roles__has_some_roles(state, session, db_user_1, db_session_1, token_1, role_1, role_2, role_name_1):
    UserStore().create_role(state, role_name_1, role_1)
    UserStore().assign_user_role(state, db_user_1, role_name_1)
    assert not AuthApi().does_user_have_roles(state, token_1, role_2)


def test__does_user_have_roles__has_all_roles(state, session, db_user_1, db_session_1, token_1, role_1, role_name_1):
    UserStore().create_role(state, role_name_1, role_1)
    UserStore().assign_user_role(state, db_user_1, role_name_1)
    assert AuthApi().does_user_have_roles(state, token_1, role_1)


def test__does_user_have_permissions__no_session(state, session, permission_1):
    assert not AuthApi().does_user_have_permissions(state, 'no-token', permission_1)


def test__does_user_have_permissions__invalid_session(mocker, state, session, permission_1):
    mocker.patch('bw.auth.session.SessionStore.get_user_from_session_token', side_effect=SessionExpired)
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


def test__revoke_discord_user_session__no_user(state, session, discord_id_1):
    response = AuthApi().revoke_discord_user_session(state, discord_id_1)
    assert response.status_code == 404


def test__revoke_bot_user_session__no_user(state, session, token_1):
    response = AuthApi().revoke_bot_user_session(state, token_1)
    assert response.status_code == 404


def test__revoke_discord_user_session__user_exists(state, session, db_discord_user_1, db_session_1):
    response = AuthApi().revoke_discord_user_session(state, db_discord_user_1.discord_id)
    assert response.status_code == 200
    assert not AuthApi().is_session_active(state, db_session_1.token)


def test__revoke_bot_user_session__user_exists(state, session, db_bot_user_1, db_session_1):
    response = AuthApi().revoke_bot_user_session(state, db_bot_user_1.bot_token)
    assert response.status_code == 200
    assert not AuthApi().is_session_active(state, db_session_1.token)


def test__create_role__success(state, session, role_1, role_name_1):
    response = AuthApi().create_role(state, role_name_1, role_1)
    assert response.status_code == 201
    assert response.contained_json['name'] == role_name_1


def test__create_role__failure(mocker, state, session, role_1, role_name_1):
    mocker.patch('bw.auth.user.UserStore.create_role', side_effect=RoleCreationFailed(role_name_1))
    response = AuthApi().create_role(state, role_name_1, role_1)
    assert response.status_code == 409


def test__assign_role__success(state, session, db_user_1, role_1, role_name_1):
    UserStore().create_role(state, role_name_1, role_1)
    response = AuthApi().assign_role(state, role_name_1, db_user_1.uuid)
    assert response.status_code == 200


def test__assign_role__no_user(state, session, role_1, role_name_1):
    UserStore().create_role(state, role_name_1, role_1)
    fake_uuid = uuid.uuid4()
    response = AuthApi().assign_role(state, role_name_1, fake_uuid)
    assert response.status_code == 404


def test__assign_role__no_role(state, session, db_user_1):
    response = AuthApi().assign_role(state, 'nonexistent_role', db_user_1.uuid)
    assert response.status_code == 404


def test__create_group_permission__success(state, session, permission_1, permission_name_1):
    response = AuthApi().create_group_permission(state, permission_name_1, permission_1)
    assert response.status_code == 201
    assert response.contained_json['name'] == permission_name_1


def test__create_group_permission__failure(mocker, state, session, permission_1, permission_name_1):
    mocker.patch('bw.auth.group.GroupStore.create_permission', side_effect=GroupPermissionCreationFailed(permission_name_1))
    response = AuthApi().create_group_permission(state, permission_name_1, permission_1)
    assert response.status_code == 409


def test__create_group__success(state, session, db_permission_1, group_name_1):
    response = AuthApi().create_group(state, group_name_1, db_permission_1.name)
    assert response.status_code == 201
    assert response.contained_json['name'] == group_name_1


def test__create_group__failure(mocker, state, session, db_permission_1, group_name_1):
    mocker.patch('bw.auth.group.GroupStore.create_group', side_effect=GroupCreationFailed(group_name_1))
    response = AuthApi().create_group(state, group_name_1, db_permission_1.name)
    assert response.status_code == 409


def test__join_group__success(state, session, db_user_1, db_group_1):
    response = AuthApi().join_group(state, db_user_1, db_group_1.name)
    assert response.status_code == 200


def test__join_group__no_group(state, session, db_user_1):
    response = AuthApi().join_group(state, db_user_1, 'nonexistent_group')
    assert response.status_code == 404


def test__join_group__assignment_failed(mocker, state, session, db_user_1, db_group_1):
    mocker.patch('bw.auth.group.GroupStore.assign_user_to_group', side_effect=GroupAssignmentFailed())
    response = AuthApi().join_group(state, db_user_1, db_group_1.name)
    assert response.status_code == 409


def test__leave_group__success(state, session, db_user_1, db_group_1):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    response = AuthApi().leave_group(state, db_user_1, db_group_1.name)
    assert response.status_code == 200


def test__leave_group__no_group(state, session, db_user_1):
    response = AuthApi().leave_group(state, db_user_1, 'nonexistent_group')
    assert response.status_code == 404


def test__auth_api__user_info_returns_uuid(state, session, db_user_1):
    response = AuthApi().user_info(state, db_user_1)
    assert response.status_code == 200
    assert response.contained_json['uuid'] == str(db_user_1.uuid)


def test__auth_api__user_info_returns_creation_date(state, session, db_user_1):
    response = AuthApi().user_info(state, db_user_1)
    assert response.status_code == 200
    assert response.contained_json['creation_date'] == db_user_1.creation_date.isoformat()


def test__auth_api__user_info_returns_empty_groups_when_no_memberships(state, session, db_user_1):
    response = AuthApi().user_info(state, db_user_1)
    assert response.status_code == 200
    assert response.contained_json['groups'] == []


def test__auth_api__user_info_returns_all_groups(state, session, db_user_1, db_group_1, db_group_2):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    GroupStore().assign_user_to_group(state, db_user_1, db_group_2)

    response = AuthApi().user_info(state, db_user_1)
    assert response.status_code == 200
    assert set(response.contained_json['groups']) == {db_group_1.name, db_group_2.name}


def test__auth_api__user_info_returns_correct_group_order(state, session, db_user_1, db_group_1, db_group_2):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    GroupStore().assign_user_to_group(state, db_user_1, db_group_2)

    response = AuthApi().user_info(state, db_user_1)
    assert response.status_code == 200
    groups = response.contained_json['groups']
    assert len(groups) == 2
    assert db_group_1.name in groups
    assert db_group_2.name in groups


def test__auth_api__user_info_different_users_different_data(state, session, db_user_1, db_user_2, db_group_1):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    # db_user_2 is not in any groups

    response1 = AuthApi().user_info(state, db_user_1)
    response2 = AuthApi().user_info(state, db_user_2)

    assert response1.contained_json['uuid'] != response2.contained_json['uuid']
    assert len(response1.contained_json['groups']) == 1
    assert len(response2.contained_json['groups']) == 0


def test__list_all_users__empty_database_returns_empty_json(state, session):
    """Test that empty database returns empty users list"""
    response = AuthApi().list_all_users(state, page=1, page_size=50)
    assert response.status_code == 200
    assert response.contained_json['users'] == []
    assert response.contained_json['total'] == 0
    assert response.contained_json['page'] == 1
    assert response.contained_json['page_size'] == 50
    assert response.contained_json['total_pages'] == 0


def test__list_all_users__single_user_returns_correct_structure(state, session, db_user_1):
    """Test that single user returns correct JSON structure"""
    response = AuthApi().list_all_users(state, page=1, page_size=50)
    assert response.status_code == 200
    assert len(response.contained_json['users']) == 1
    assert response.contained_json['total'] == 1


def test__list_all_users__pagination_works(state, session):
    """Test that pagination parameters are passed through"""
    # Create 3 users
    for _ in range(3):
        UserStore().create_user(state)

    response = AuthApi().list_all_users(state, page=1, page_size=2)
    assert response.status_code == 200
    assert len(response.contained_json['users']) == 2
    assert response.contained_json['total'] == 3
    assert response.contained_json['page'] == 1
    assert response.contained_json['total_pages'] == 2


def test__list_all_users__second_page_works(state, session):
    """Test that second page returns remaining users"""
    # Create 3 users
    for _ in range(3):
        UserStore().create_user(state)

    response = AuthApi().list_all_users(state, page=2, page_size=2)
    assert response.status_code == 200
    assert len(response.contained_json['users']) == 1
    assert response.contained_json['page'] == 2


def test__list_all_users__default_pagination_values(state, session):
    """Test that default pagination values work"""
    UserStore().create_user(state)

    response = AuthApi().list_all_users(state)
    assert response.status_code == 200
    assert response.contained_json['page'] == 1
    assert response.contained_json['page_size'] == 50


# Tests for get_all_roles


def test__get_all_roles__empty_database_returns_empty_json(state, session):
    """Test that empty database returns empty roles list"""
    response = AuthApi().get_all_roles(state)
    assert response.status_code == 200
    assert response.contained_json['roles'] == []


def test__get_all_roles__single_role_returns_correctly(state, session, db_role_1, role_name_1, role_1):
    """Test that single role is returned with correct structure"""
    response = AuthApi().get_all_roles(state)
    assert response.status_code == 200
    assert len(response.contained_json['roles']) == 1

    role = response.contained_json['roles'][0]
    assert role['name'] == role_name_1
    assert role == {'name': role_name_1, **role_1.as_dict()}


def test__get_all_roles__multiple_roles_returns_all(
    state, session, db_role_1, db_role_2, role_name_1, role_name_2, role_1, role_2
):
    """Test that all roles are returned"""
    response = AuthApi().get_all_roles(state)
    assert response.status_code == 200
    assert len(response.contained_json['roles']) == 2

    role_names = {role['name'] for role in response.contained_json['roles']}
    assert role_names == {role_name_1, role_name_2}


def test__get_all_roles__role_permissions_included(state, session, db_role_1, role_1):
    """Test that role permissions are included in response"""
    response = AuthApi().get_all_roles(state)
    role = response.contained_json['roles'][0]

    for key, value in role_1.as_dict().items():
        assert role[key] == value


# Tests for get_all_permissions


def test__get_all_permissions__empty_database_returns_empty_json(state, session):
    """Test that empty database returns empty permissions list"""
    response = AuthApi().get_all_permissions(state)
    assert response.status_code == 200
    assert response.contained_json['permissions'] == []


def test__get_all_permissions__single_permission_returns_correctly(
    state, session, db_permission_1, permission_name_1, permission_1
):
    """Test that single permission is returned with correct structure"""
    response = AuthApi().get_all_permissions(state)
    assert response.status_code == 200
    assert len(response.contained_json['permissions']) == 1

    perm = response.contained_json['permissions'][0]
    assert perm['name'] == permission_name_1
    assert perm == {'name': permission_name_1, **permission_1.as_dict()}


def test__get_all_permissions__multiple_permissions_returns_all(
    state, session, db_permission_1, db_permission_2, db_permission_3
):
    """Test that all permissions are returned"""
    response = AuthApi().get_all_permissions(state)
    assert response.status_code == 200
    assert len(response.contained_json['permissions']) == 3

    perm_names = {perm['name'] for perm in response.contained_json['permissions']}
    assert perm_names == {db_permission_1.name, db_permission_2.name, db_permission_3.name}


def test__get_all_permissions__permission_grants_included(state, session, db_permission_1, permission_1):
    """Test that permission grants are included in response"""
    response = AuthApi().get_all_permissions(state)
    perm = response.contained_json['permissions'][0]

    for key, value in permission_1.as_dict().items():
        assert perm[key] == value


# Tests for get_all_groups


def test__get_all_groups__empty_database_returns_empty_json(state, session):
    """Test that empty database returns empty groups list"""
    response = AuthApi().get_all_groups(state)
    assert response.status_code == 200
    assert response.contained_json['groups'] == []


def test__get_all_groups__single_group_returns_correctly(state, session, db_group_1, group_name_1):
    """Test that single group is returned with correct structure"""
    response = AuthApi().get_all_groups(state)
    assert response.status_code == 200
    assert len(response.contained_json['groups']) == 1

    group = response.contained_json['groups'][0]
    assert group['id'] == db_group_1.id
    assert group['name'] == group_name_1
    assert group['permissions'] == db_group_1.permissions


def test__get_all_groups__multiple_groups_returns_all(state, session, db_group_1, db_group_2, db_group_3):
    """Test that all groups are returned"""
    response = AuthApi().get_all_groups(state)
    assert response.status_code == 200
    assert len(response.contained_json['groups']) == 3

    group_ids = {group['id'] for group in response.contained_json['groups']}
    assert group_ids == {db_group_1.id, db_group_2.id, db_group_3.id}


def test__get_all_groups__group_permission_id_included(state, session, db_group_1, db_permission_1):
    """Test that group permission ID is included"""
    response = AuthApi().get_all_groups(state)
    group = response.contained_json['groups'][0]
    assert group['permissions'] == db_permission_1.id


# Tests for delete_role


def test__delete_role__success_returns_ok(state, session, db_role_1, role_name_1):
    """Test that deleting existing role returns OK"""
    response = AuthApi().delete_role(state, role_name_1)
    assert response.status_code == 200


def test__delete_role__actually_deletes_role(state, session, db_role_1, role_name_1):
    """Test that role is actually deleted from database"""
    AuthApi().delete_role(state, role_name_1)

    # Verify it's gone
    roles = UserStore().get_all_roles(state)
    assert len(roles) == 0


def test__delete_role__nonexistent_role_returns_error(state, session):
    """Test that deleting non-existent role returns 404"""
    response = AuthApi().delete_role(state, 'nonexistent_role')
    assert response.status_code == 404


def test__delete_role__removes_from_users(state, session, db_role_1, db_user_1, role_name_1):
    """Test that role is removed from users who have it"""
    UserStore().assign_user_role(state, db_user_1, role_name_1)
    AuthApi().delete_role(state, role_name_1)

    user_role = UserStore().get_users_role(state, db_user_1)
    assert user_role is None


def test__delete_role__does_not_affect_other_roles(state, session, db_role_1, db_role_2, role_name_1):
    """Test that deleting one role doesn't affect others"""
    AuthApi().delete_role(state, role_name_1)

    roles = UserStore().get_all_roles(state)
    assert len(roles) == 1
    assert roles[0].id == db_role_2.id


# Tests for delete_permission


def test__delete_permission__success_returns_ok(state, session, db_permission_1, permission_name_1):
    """Test that deleting existing permission returns OK"""
    response = AuthApi().delete_permission(state, permission_name_1)
    assert response.status_code == 200


def test__delete_permission__actually_deletes_permission(state, session, db_permission_1, permission_name_1):
    """Test that permission is actually deleted from database"""
    AuthApi().delete_permission(state, permission_name_1)

    # Verify it's gone
    permissions = GroupStore().get_all_permissions(state)
    assert len(permissions) == 0


def test__delete_permission__nonexistent_permission_returns_error(state, session):
    """Test that deleting non-existent permission returns 404"""
    response = AuthApi().delete_permission(state, 'nonexistent_permission')
    assert response.status_code == 404


def test__delete_permission__does_not_affect_other_permissions(
    state, session, db_permission_1, db_permission_2, permission_name_1
):
    """Test that deleting one permission doesn't affect others"""
    AuthApi().delete_permission(state, permission_name_1)

    permissions = GroupStore().get_all_permissions(state)
    assert len(permissions) == 1
    assert permissions[0].id == db_permission_2.id


# Tests for delete_group


def test__delete_group__success_returns_ok(state, session, db_group_1, group_name_1):
    """Test that deleting existing group returns OK"""
    response = AuthApi().delete_group(state, group_name_1)
    assert response.status_code == 200


def test__delete_group__actually_deletes_group(state, session, db_group_1, group_name_1):
    """Test that group is actually deleted from database"""
    AuthApi().delete_group(state, group_name_1)

    # Verify it's gone
    groups = GroupStore().get_all_groups(state)
    assert len(groups) == 0


def test__delete_group__nonexistent_group_succeeds(state, session):
    """Test that deleting non-existent group doesn't error"""
    response = AuthApi().delete_group(state, 'nonexistent_group')
    assert response.status_code == 200


def test__delete_group__removes_user_associations(state, session, db_group_1, db_user_1, group_name_1):
    """Test that user associations are removed"""
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    AuthApi().delete_group(state, group_name_1)

    groups = GroupStore().get_user_groups(state, db_user_1)
    assert len(groups) == 0


def test__delete_group__does_not_affect_other_groups(state, session, db_group_1, db_group_2, group_name_1):
    """Test that deleting one group doesn't affect others"""
    AuthApi().delete_group(state, group_name_1)

    groups = GroupStore().get_all_groups(state)
    assert len(groups) == 1
    assert groups[0].id == db_group_2.id


# Tests for edit_role


def test__edit_role__success_returns_json_with_name(state, session, db_role_1, role_name_1, role_2):
    """Test that editing role returns JSON with role name"""
    response = AuthApi().edit_role(state, role_name_1, role_2)
    assert response.status_code == 200
    assert response.contained_json['name'] == role_name_1


def test__edit_role__actually_updates_role(state, session, db_role_1, role_name_1, role_1, role_2):
    """Test that role is actually updated in database"""
    AuthApi().edit_role(state, role_name_1, role_2)

    roles = UserStore().get_all_roles(state)
    updated_role = roles[0]
    assert updated_role.into_roles().as_dict() == role_2.as_dict()
    assert updated_role.into_roles().as_dict() != role_1.as_dict()


def test__edit_role__nonexistent_role_returns_error(state, session, role_1):
    """Test that editing non-existent role returns 404"""
    response = AuthApi().edit_role(state, 'nonexistent_role', role_1)
    assert response.status_code == 404


def test__edit_role__keeps_same_id(state, session, db_role_1, role_name_1, role_2):
    """Test that editing role keeps the same ID"""
    original_id = db_role_1.id
    AuthApi().edit_role(state, role_name_1, role_2)

    roles = UserStore().get_all_roles(state)
    assert roles[0].id == original_id


def test__edit_role__does_not_affect_other_roles(state, session, db_role_1, db_role_2, role_name_1, role_2):
    """Test that editing one role doesn't affect others"""
    original_role_2_data = db_role_2.into_roles().as_dict()
    AuthApi().edit_role(state, role_name_1, role_2)

    roles = UserStore().get_all_roles(state)
    role_2_after = [r for r in roles if r.id == db_role_2.id][0]
    assert role_2_after.into_roles().as_dict() == original_role_2_data


# Tests for edit_permission


def test__edit_permission__success_returns_json_with_name(state, session, db_permission_1, permission_name_1, permission_2):
    """Test that editing permission returns JSON with permission name"""
    response = AuthApi().edit_permission(state, permission_name_1, permission_2)
    assert response.status_code == 200
    assert response.contained_json['name'] == permission_name_1


def test__edit_permission__actually_updates_permission(
    state, session, db_permission_1, permission_name_1, permission_1, permission_2
):
    """Test that permission is actually updated in database"""
    AuthApi().edit_permission(state, permission_name_1, permission_2)

    permissions = GroupStore().get_all_permissions(state)
    updated_perm = permissions[0]
    assert updated_perm.into_permissions().as_dict() == permission_2.as_dict()
    assert updated_perm.into_permissions().as_dict() != permission_1.as_dict()


def test__edit_permission__nonexistent_permission_returns_error(state, session, permission_1):
    """Test that editing non-existent permission returns 404"""
    response = AuthApi().edit_permission(state, 'nonexistent_permission', permission_1)
    assert response.status_code == 404


def test__edit_permission__keeps_same_id(state, session, db_permission_1, permission_name_1, permission_2):
    """Test that editing permission keeps the same ID"""
    original_id = db_permission_1.id
    AuthApi().edit_permission(state, permission_name_1, permission_2)

    permissions = GroupStore().get_all_permissions(state)
    assert permissions[0].id == original_id


def test__edit_permission__does_not_affect_other_permissions(
    state, session, db_permission_1, db_permission_2, permission_name_1, permission_2
):
    """Test that editing one permission doesn't affect others"""
    original_perm_2_data = db_permission_2.into_permissions().as_dict()
    AuthApi().edit_permission(state, permission_name_1, permission_2)

    permissions = GroupStore().get_all_permissions(state)
    perm_2_after = [p for p in permissions if p.id == db_permission_2.id][0]
    assert perm_2_after.into_permissions().as_dict() == original_perm_2_data


def test__edit_permission__groups_using_permission_get_updated_permissions(
    state, session, db_group_1, db_user_1, db_permission_1, permission_name_1, permission_1, permission_2
):
    """Test that groups using edited permission get the updated permissions"""
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)

    # User should have permission_1 grants
    perms_before = GroupStore().get_all_permissions_user_has(state, db_user_1)
    assert perms_before.as_dict() == permission_1.as_dict()

    # Edit the permission
    AuthApi().edit_permission(state, permission_name_1, permission_2)

    # User should now have permission_2 grants
    perms_after = GroupStore().get_all_permissions_user_has(state, db_user_1)
    assert perms_after.as_dict() == permission_2.as_dict()
