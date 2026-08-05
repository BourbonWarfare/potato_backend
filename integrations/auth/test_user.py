# ruff: noqa: F811, F401

import pytest
from sqlalchemy import select

from bw.auth.group import GroupStore
from bw.auth.user import UserStore
from bw.error import AuthError, DbError, DiscordUserAlreadyExists, NoRoleWithName, NoUserWithGivenCredentials, RoleCreationFailed
from bw.models.auth import BotUser, DiscordUser, Role, User, UserGroup
from integrations.auth.fixtures import (
    db_bot_user_1,
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
    group_name_1,
    group_name_2,
    non_db_user_1,
    permission_1,
    permission_2,
    permission_name_1,
    permission_name_2,
    role_1,
    role_2,
    role_name_1,
    role_name_2,
    token_1,
)


class TestUserStoreUserLookup:
    def test__create_user__returns_user(self, state, session):
        UserStore().create_user(state)

    def test__user_from_id__doesnt_raise(self, state, db_user_1):
        user = UserStore().user_from_id(state, db_user_1.id)
        assert user.id == db_user_1.id
        assert user.creation_date == db_user_1.creation_date
        assert user.role == db_user_1.role

    def test__user_from_id__raises(self, state, session):
        with pytest.raises(NoUserWithGivenCredentials):
            UserStore().user_from_id(state, 1)

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


class TestUserStoreDiscordUser:
    def test__link_discord_user__linking_invalid_user_excepts(self, state, discord_id_1, non_db_user_1):
        with pytest.raises(NoUserWithGivenCredentials):
            UserStore().link_discord_user(state, non_db_user_1, discord_id_1)
