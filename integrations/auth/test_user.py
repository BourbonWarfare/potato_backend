# ruff: noqa: F811, F401

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.sql.functions import user

from bw.auth.group import GroupStore
from bw.auth.user import UserStore
from bw.error import (
    AuthError,
    BourbonUserAlreadyExists,
    DbError,
    DiscordUserAlreadyExists,
    NoRoleWithName,
    NoUserWithGivenCredentials,
    RoleCreationFailed,
)
from bw.models.auth import BotUser, BourbonUser, DiscordUser, Role, User, UserGroup
from integrations.auth.fixtures import (
    db_bot_user_1,
    db_bourbon_user_1,
    db_discord_user_1,
    db_group_1,
    db_group_2,
    db_permission_1,
    db_permission_2,
    db_role_1,
    db_role_2,
    db_user_1,
    db_user_2,
    discord_id_1,
    email_1,
    email_2,
    group_name_1,
    group_name_2,
    non_db_user_1,
    password_1,
    permission_1,
    permission_2,
    permission_name_1,
    permission_name_2,
    role_1,
    role_2,
    role_name_1,
    role_name_2,
    salt_1,
    token_1,
    username_1,
    username_2,
)


class TestUserStoreUserLookup:
    def test__create_user__returns_user(self, state):
        user = UserStore().create_user(state)
        assert user.id is not None
        assert user.uuid is not None

        retrieved = UserStore().user_from_id(state, user.id)
        assert retrieved.id == user.id

    def test__user_from_id__doesnt_raise(self, state, db_user_1):
        user = UserStore().user_from_id(state, db_user_1.id)
        assert user.id == db_user_1.id
        assert user.creation_date == db_user_1.creation_date
        assert user.role == db_user_1.role

    def test__user_from_id__raises(self, state, session):
        with pytest.raises(NoUserWithGivenCredentials):
            UserStore().user_from_id(state, 1)

    def test__user_from_uuid__doesnt_raise(self, state, db_user_1):
        user = UserStore().user_from_uuid(state, db_user_1.uuid)
        assert user.id == db_user_1.id
        assert user.creation_date == db_user_1.creation_date

    def test__user_from_uuid__raises(self, state):
        with pytest.raises(NoUserWithGivenCredentials):
            UserStore().user_from_uuid(state, uuid.uuid4())

    def test__user_from_email__doesnt_raise(self, state, db_user_1, email_1, db_bourbon_user_1):
        user = UserStore().user_from_email(state, email_1)
        assert user.id == db_user_1.id

    def test__user_from_email__raises(self, state, email_1):
        with pytest.raises(NoUserWithGivenCredentials):
            UserStore().user_from_email(state, email_1)

    def test__user_from_username__doesnt_raise(self, state, db_user_1, username_1, db_bourbon_user_1):
        user = UserStore().user_from_username(state, username_1)
        assert user.id == db_user_1.id

    def test__user_from_username__raises(self, state):
        with pytest.raises(NoUserWithGivenCredentials):
            UserStore().user_from_username(state, 'nonexistent_user')

    def test__user_from_discord_id__doesnt_raise(self, state, db_user_1, db_discord_user_1):
        user = UserStore().user_from_discord_id(state, db_discord_user_1.discord_id)
        assert user.id == db_user_1.id
        assert user.creation_date == db_user_1.creation_date
        assert user.role == db_user_1.role

    def test__user_from_discord_id__raises(self, state, discord_id_1):
        with pytest.raises(NoUserWithGivenCredentials):
            UserStore().user_from_discord_id(state, discord_id_1)

    def test__user_from_bot_token__doesnt_raise(self, state, db_user_1, db_bot_user_1):
        user = UserStore().user_from_bot_token(state, db_bot_user_1.bot_token)
        assert user.id == db_user_1.id
        assert user.creation_date == db_user_1.creation_date
        assert user.role == db_user_1.role

    def test__user_from_bot_token__raises(self, state, session):
        with pytest.raises(NoUserWithGivenCredentials):
            UserStore().user_from_bot_token(state, 'no token')


class TestUserStoreBotUser:
    def test__link_bot_user__linking_invalid_user_excepts(self, state, non_db_user_1):
        with pytest.raises(NoUserWithGivenCredentials):
            UserStore().link_bot_user(state, non_db_user_1)

    def test__link_bot_user__linking_valid_user_no_except(self, mocker, state, db_user_1, token_1):
        mocker.patch('secrets.token_urlsafe', return_value=token_1)
        bot_user = UserStore().link_bot_user(state, db_user_1)

        assert bot_user.bot_token == token_1
        assert bot_user.user_id == db_user_1.id

    def test__link_bot_user__cant_link_many(self, state, db_user_1):
        UserStore().link_bot_user(state, db_user_1)
        with pytest.raises(DbError):
            UserStore().link_bot_user(state, db_user_1)

    def test__link_bot_user__can_get_user_from_generated_token(self, state, db_user_1):
        bot_user = UserStore().link_bot_user(state, db_user_1)
        user = UserStore().user_from_bot_token(state, bot_user.bot_token)
        assert user.id == db_user_1.id
        assert user.creation_date == db_user_1.creation_date
        assert user.role == db_user_1.role

    def test__delete_bot_user__by_bot_user(self, state, db_bot_user_1):
        UserStore().delete_bot_user(state, db_bot_user_1)
        with pytest.raises(NoUserWithGivenCredentials):
            UserStore().user_from_bot_token(state, db_bot_user_1.bot_token)

    def test__delete_bot_user__by_user(self, state, db_user_1, db_bot_user_1):
        UserStore().delete_bot_user(state, db_user_1)
        with pytest.raises(NoUserWithGivenCredentials):
            UserStore().user_from_bot_token(state, db_bot_user_1.bot_token)

    def test__delete_bot_user__invalid_args_raises(self, state):
        with pytest.raises(AuthError):
            UserStore().delete_bot_user(state, 'invalid_type')


class TestUserStoreDiscordUser:
    def test__link_discord_user__linking_invalid_user_excepts(self, state, discord_id_1, non_db_user_1):
        with pytest.raises(NoUserWithGivenCredentials):
            UserStore().link_discord_user(state, discord_id_1, non_db_user_1)

    def test__link_discord_user__valid(self, state, db_user_1, discord_id_1):
        discord_user = UserStore().link_discord_user(state, discord_id_1, db_user_1)
        assert discord_user.user_id == db_user_1.id
        assert discord_user.discord_id == discord_id_1

        retrieved = UserStore().user_from_discord_id(state, discord_id_1)
        assert retrieved.id == db_user_1.id

    def test__link_discord_user__already_exists_raises(self, state, db_user_1, db_user_2, discord_id_1):
        UserStore().link_discord_user(state, discord_id_1, db_user_1)
        with pytest.raises(DiscordUserAlreadyExists):
            UserStore().link_discord_user(state, discord_id_1, db_user_2)

    def test__delete_discord_user__by_discord_user(self, state, db_discord_user_1, discord_id_1):
        UserStore().delete_discord_user(state, db_discord_user_1)
        with pytest.raises(NoUserWithGivenCredentials):
            UserStore().user_from_discord_id(state, discord_id_1)

    def test__delete_discord_user__by_user(self, state, db_user_1, db_discord_user_1, discord_id_1):
        UserStore().delete_discord_user(state, db_user_1)
        with pytest.raises(NoUserWithGivenCredentials):
            UserStore().user_from_discord_id(state, discord_id_1)

    def test__delete_discord_user__invalid_args_raises(self, state):
        with pytest.raises(AuthError):
            UserStore().delete_discord_user(state, 'invalid_type')


class TestUserStoreBourbonUser:
    def test__link_bourbon_user__valid(self, state, db_user_1, email_1, username_1, password_1):
        bourbon_user = UserStore().link_bourbon_user(state, username_1, email_1, password_1, db_user_1)
        assert bourbon_user.user_id == db_user_1.id
        assert bourbon_user.username == username_1
        assert bourbon_user.email == email_1
        assert bourbon_user.password_hashed != password_1
        assert bourbon_user.verified is False

    def test__link_bourbon_user__username_already_exists_raises(
        self, state, db_user_1, db_user_2, email_2, password_1, username_1, username_2, db_bourbon_user_1
    ):
        with pytest.raises(BourbonUserAlreadyExists):
            UserStore().link_bourbon_user(state, username_1, email_2, password_1, db_user_2)

    def test__link_bourbon_user__email_already_exists_raises(
        self, state, db_user_1, db_user_2, email_1, password_1, username_1, username_2, db_bourbon_user_1
    ):
        with pytest.raises(BourbonUserAlreadyExists):
            UserStore().link_bourbon_user(state, username_2, email_1, password_1, db_user_2)

    def test__bourbon_user_from_user__doesnt_raise(self, state, db_user_1, email_1, username_1, db_bourbon_user_1):
        retrieved = UserStore().bourbon_user_from_user(state, db_user_1)
        assert retrieved.id == db_bourbon_user_1.id
        assert retrieved.username == username_1

    def test__bourbon_user_from_user__raises(self, state, db_user_1):
        with pytest.raises(NoUserWithGivenCredentials):
            UserStore().bourbon_user_from_user(state, db_user_1)

    def test__verify_bourbon_user_from_email(self, state, db_user_1, email_1, db_bourbon_user_1):
        UserStore().verify_bourbon_user_from_email(state, email_1)

        bourbon_user = UserStore().bourbon_user_from_user(state, db_user_1)
        assert bourbon_user.verified is True

    def test__delete_bourbon_user__by_bourbon_user(self, state, db_user_1, email_1, db_bourbon_user_1):
        UserStore().delete_bourbon_user(state, db_bourbon_user_1)
        with pytest.raises(NoUserWithGivenCredentials):
            UserStore().bourbon_user_from_user(state, db_user_1)

    def test__delete_bourbon_user__by_user(self, state, db_user_1, email_1, db_bourbon_user_1):
        UserStore().delete_bourbon_user(state, db_user_1)
        with pytest.raises(NoUserWithGivenCredentials):
            UserStore().bourbon_user_from_user(state, db_user_1)

    def test__delete_bourbon_user__invalid_args_raises(self, state):
        with pytest.raises(AuthError):
            UserStore().delete_bourbon_user(state, 'invalid_type')


class TestUserStoreDeleteUser:
    def test__delete_user__removes_user_and_linked_accounts(
        self, state, db_user_1, discord_id_1, email_1, username_1, password_1
    ):
        UserStore().link_discord_user(state, discord_id_1, db_user_1)
        UserStore().link_bot_user(state, db_user_1)
        UserStore().link_bourbon_user(state, username_1, email_1, password_1, db_user_1)

        UserStore().delete_user(state, db_user_1)

        with pytest.raises(NoUserWithGivenCredentials):
            UserStore().user_from_id(state, db_user_1.id)


class TestUserStoreRoles:
    def test__create_role__valid(self, state, role_name_1, role_1):
        role = UserStore().create_role(state, role_name_1, role_1)
        assert role.name == role_name_1
        assert role.can_create_role == role_1.can_create_role
        assert role.can_create_group == role_1.can_create_group

    def test__create_role__already_exists_raises(self, state, role_name_1, role_1):
        UserStore().create_role(state, role_name_1, role_1)
        with pytest.raises(RoleCreationFailed):
            UserStore().create_role(state, role_name_1, role_1)

    def test__edit_role__valid(self, state, db_role_1, role_2):
        updated_role = UserStore().edit_role(state, db_role_1.name, role_2)
        assert updated_role.can_create_group == role_2.can_create_group
        assert updated_role.can_create_role == role_2.can_create_role

    def test__edit_role__nonexistent_raises(self, state, role_1):
        with pytest.raises(NoRoleWithName):
            UserStore().edit_role(state, 'nonexistent_role', role_1)

    def test__assign_user_role__and_get_users_role(self, state, db_user_1, db_role_1, role_1):
        UserStore().assign_user_role(state, db_user_1, db_role_1.name)
        assigned_role = UserStore().get_users_role(state, db_user_1)
        assert assigned_role.can_create_role == role_1.can_create_role
        assert assigned_role.can_create_group == role_1.can_create_group

    def test__assign_user_role__nonexistent_role_raises(self, state, db_user_1):
        with pytest.raises(NoRoleWithName):
            UserStore().assign_user_role(state, db_user_1, 'nonexistent_role')

    def test__get_users_role__unassigned_returns_none(self, state, db_user_1):
        role = UserStore().get_users_role(state, db_user_1)
        assert role is None

    def test__delete_role__unassigns_from_users_and_deletes(self, state, db_user_1, db_role_1):
        UserStore().assign_user_role(state, db_user_1, db_role_1.name)
        UserStore().delete_role(state, db_role_1.name)

        assert UserStore().get_users_role(state, db_user_1) is None
        with pytest.raises(NoRoleWithName):
            UserStore().delete_role(state, db_role_1.name)

    def test__delete_role__nonexistent_raises(self, state):
        with pytest.raises(NoRoleWithName):
            UserStore().delete_role(state, 'nonexistent_role')

    def test__get_all_roles(self, state, db_role_1, db_role_2):
        roles = UserStore().get_all_roles(state)
        assert len(roles) == 2
        role_names = [role.name for role in roles]
        assert db_role_1.name in role_names
        assert db_role_2.name in role_names


class TestUserStorePagination:
    def test__get_all_users_paginated(self, state, db_user_1, db_user_2, db_role_1, discord_id_1):
        UserStore().assign_user_role(state, db_user_1, db_role_1.name)
        UserStore().link_discord_user(state, discord_id_1, db_user_1)

        result = UserStore().get_all_users_paginated(state, page=1, page_size=10)

        assert result['total'] == 2
        assert result['page'] == 1
        assert result['page_size'] == 10
        assert result['total_pages'] == 1
        assert len(result['users']) == 2

        user1_data = next(u for u in result['users'] if u['id'] == db_user_1.id)
        assert user1_data['role'] == db_role_1.name
        assert user1_data['connected_apps']['discord'] is True
        assert user1_data['connected_apps']['bot'] is False
