# ruff: noqa: F811, F401

import pytest

from sqlalchemy import select

from bw.auth.user import UserStore
from bw.models.auth import User, DiscordUser, BotUser
from bw.error import DbError, NoUserWithGivenCredentials, AuthError
from integrations.fixtures import (
    state,
    session,
    non_db_user_1,
    db_user_1,
    token_1,
    db_discord_user_1,
    db_bot_user_1,
    discord_id_1,
)


def test__create_user__returns_user(state, session):
    UserStore().create_user(state)


def test__user_from_id__doesnt_raise(state, session, db_user_1):
    user = UserStore().user_from_id(state, db_user_1.id)
    assert user.id == db_user_1.id
    assert user.creation_date == db_user_1.creation_date
    assert user.role == db_user_1.role


def test__user_from_id__raises(state, session):
    with pytest.raises(NoUserWithGivenCredentials):
        UserStore().user_from_id(state, 1)


def test__user_from_discord_id__doesnt_raise(state, session, db_user_1, db_discord_user_1):
    user = UserStore().user_from_discord_id(state, db_discord_user_1.discord_id)
    assert user.id == db_user_1.id
    assert user.creation_date == db_user_1.creation_date
    assert user.role == db_user_1.role


def test__user_from_discord_id__raises(state, session):
    with pytest.raises(NoUserWithGivenCredentials):
        UserStore().user_from_discord_id(state, 1)


def test__user_from_bot_token__doesnt_raise(state, session, db_user_1, db_bot_user_1):
    user = UserStore().user_from_bot_token(state, db_bot_user_1.bot_token)
    assert user.id == db_user_1.id
    assert user.creation_date == db_user_1.creation_date
    assert user.role == db_user_1.role


def test__user_from_bot_token__raises(state, session):
    with pytest.raises(NoUserWithGivenCredentials):
        UserStore().user_from_bot_token(state, 'no token')


def test__link_bot_user__linking_invalid_user_excepts(state, session, non_db_user_1):
    with pytest.raises(NoUserWithGivenCredentials):
        UserStore().link_bot_user(state, non_db_user_1)


def test__link_bot_user__linking_valid_user_no_except(mocker, state, session, db_user_1, token_1):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    bot_user = UserStore().link_bot_user(state, db_user_1)

    assert bot_user.bot_token == token_1
    assert bot_user.user_id == db_user_1.id


def test__link_bot_user__cant_link_many(state, session, db_user_1):
    UserStore().link_bot_user(state, db_user_1)
    with pytest.raises(DbError):
        UserStore().link_bot_user(state, db_user_1)


def test__link_bot_user__can_get_user_from_generated_token(state, session, db_user_1):
    bot_user = UserStore().link_bot_user(state, db_user_1)
    user = UserStore().user_from_bot_token(state, bot_user.bot_token)
    assert user.id == db_user_1.id
    assert user.creation_date == db_user_1.creation_date
    assert user.role == db_user_1.role


def test__link_discord_user__linking_invalid_user_excepts(state, session, discord_id_1, non_db_user_1):
    with pytest.raises(NoUserWithGivenCredentials):
        UserStore().link_discord_user(state, discord_id_1, non_db_user_1)


def test__link_discord_user__linking_valid_user_no_except(mocker, state, session, discord_id_1, db_user_1, token_1):
    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    discord_user = UserStore().link_discord_user(state, discord_id_1, db_user_1)

    assert discord_user.discord_id == discord_id_1
    assert discord_user.user_id == db_user_1.id


def test__link_discord_user__cant_link_many(state, session, discord_id_1, db_user_1):
    UserStore().link_discord_user(state, discord_id_1, db_user_1)
    with pytest.raises(DbError):
        UserStore().link_discord_user(state, discord_id_1, db_user_1)


def test__link_discord_user__can_get_user_from_generated_token(state, session, discord_id_1, db_user_1):
    discord_user = UserStore().link_discord_user(state, discord_id_1, db_user_1)
    user = UserStore().user_from_discord_id(state, discord_user.discord_id)
    assert user.id == db_user_1.id
    assert user.creation_date == db_user_1.creation_date
    assert user.role == db_user_1.role


def test__delete_user__can_delete_valid_user(state, session, db_user_1):
    with state.Session.begin() as session:
        query = select(User).where(User.id == db_user_1.id)
        row = session.execute(query).first()
        assert row is not None

    UserStore().delete_user(state, db_user_1)

    with state.Session.begin() as session:
        query = select(User).where(User.id == db_user_1.id)
        row = session.execute(query).first()
        assert row is None


def test__delete_user__can_try_delete_invalid_user(state, session, non_db_user_1):
    with state.Session.begin() as session:
        query = select(User).where(User.id == non_db_user_1.id)
        row = session.execute(query).first()
        assert row is None

    UserStore().delete_user(state, non_db_user_1)

    with state.Session.begin() as session:
        query = select(User).where(User.id == non_db_user_1.id)
        row = session.execute(query).first()
        assert row is None


def test__delete_user__deletes_discord_user(state, session, db_discord_user_1, db_user_1):
    UserStore().delete_user(state, db_user_1)

    with state.Session.begin() as session:
        query = select(User).where(User.id == db_user_1.id)
        row = session.execute(query).first()
        assert row is None

    with state.Session.begin() as session:
        query = select(DiscordUser).where(DiscordUser.id == db_discord_user_1.id)
        row = session.execute(query).first()
        assert row is None


def test__delete_user__deletes_bot_user(state, session, db_bot_user_1, db_user_1):
    UserStore().delete_user(state, db_user_1)

    with state.Session.begin() as session:
        query = select(User).where(User.id == db_user_1.id)
        row = session.execute(query).first()
        assert row is None

    with state.Session.begin() as session:
        query = select(BotUser).where(BotUser.id == db_bot_user_1.id)
        row = session.execute(query).first()
        assert row is None


def test__delete_discord_user__deletes_discord_user_from_user(state, session, db_discord_user_1, db_user_1):
    UserStore().delete_discord_user(state, db_user_1)

    with state.Session.begin() as session:
        query = select(User).where(User.id == db_user_1.id)
        row = session.execute(query).first()
        assert row is not None

    with state.Session.begin() as session:
        query = select(DiscordUser).where(DiscordUser.id == db_discord_user_1.id)
        row = session.execute(query).first()
        assert row is None


def test__delete_discord_user__deletes_discord_user_from_discord_user(state, session, db_discord_user_1, db_user_1):
    UserStore().delete_discord_user(state, db_discord_user_1)

    with state.Session.begin() as session:
        query = select(User).where(User.id == db_user_1.id)
        row = session.execute(query).first()
        assert row is not None

    with state.Session.begin() as session:
        query = select(DiscordUser).where(DiscordUser.id == db_discord_user_1.id)
        row = session.execute(query).first()
        assert row is None


def test__delete_discord_user__raises_on_bad_argument(state, session):
    with pytest.raises(AuthError):
        UserStore().delete_discord_user(state, None)


def test__delete_bot_user__deletes_bot_user_from_user(state, session, db_bot_user_1, db_user_1):
    UserStore().delete_bot_user(state, db_user_1)

    with state.Session.begin() as session:
        query = select(User).where(User.id == db_user_1.id)
        row = session.execute(query).first()
        assert row is not None

    with state.Session.begin() as session:
        query = select(BotUser).where(BotUser.id == db_bot_user_1.id)
        row = session.execute(query).first()
        assert row is None


def test__delete_bot_user__deletes_bot_user_from_bot_user(state, session, db_bot_user_1, db_user_1):
    UserStore().delete_bot_user(state, db_bot_user_1)

    with state.Session.begin() as session:
        query = select(User).where(User.id == db_user_1.id)
        row = session.execute(query).first()
        assert row is not None

    with state.Session.begin() as session:
        query = select(BotUser).where(BotUser.id == db_bot_user_1.id)
        row = session.execute(query).first()
        assert row is None


def test__delete_bot_user__raises_on_bad_argument(state, session):
    with pytest.raises(AuthError):
        UserStore().delete_bot_user(state, None)
