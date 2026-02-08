# ruff: noqa: F811, F401

import pytest

from sqlalchemy import select

from bw.auth.user import UserStore
from bw.auth.group import GroupStore
from bw.models.auth import User, DiscordUser, BotUser, Role, Session, UserGroup
from bw.error import DbError, NoUserWithGivenCredentials, AuthError, RoleCreationFailed, NoRoleWithName, DiscordUserAlreadyExists
from integrations.auth.fixtures import (
    state,
    session,
    non_db_user_1,
    db_user_1,
    token_1,
    db_discord_user_1,
    db_bot_user_1,
    discord_id_1,
    role_1,
    role_2,
    db_user_2,
    db_group_1,
    db_permission_1,
    group_name_1,
    permission_1,
    permission_name_1,
    role_name_1,
    role_name_2,
    db_role_1,
    db_role_2,
    db_group_2,
    group_name_2,
    db_permission_2,
    permission_2,
    permission_name_2,
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
    with pytest.raises(DiscordUserAlreadyExists):
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


def test__create_role__can_create_role(state, session, role_1):
    UserStore().create_role(state, 'my_role', role_1)


def test__create_role__create_duplicate_raises(state, session, role_1):
    UserStore().create_role(state, 'my_role', role_1)
    with pytest.raises(RoleCreationFailed):
        UserStore().create_role(state, 'my_role', role_1)


def test__edit_role__can_edit_role(state, session, role_1, role_2):
    db_role_1 = UserStore().create_role(state, 'my_role', role_1)
    new_role = UserStore().edit_role(state, 'my_role', role_2)
    assert new_role.id == db_role_1.id
    assert new_role.into_roles().as_dict() == role_2.as_dict()
    with state.Session.begin() as session:
        query = select(Role).where(Role.name == 'my_role')
        db_role = session.execute(query).one()[0]
        assert db_role.into_roles().as_dict() == role_2.as_dict()


def test__edit_role__cant_edit_non_existing_role(state, session, role_1):
    with pytest.raises(NoRoleWithName):
        UserStore().edit_role(state, 'my_role', role_1)


def test__delete_role__can_delete_role_simple(state, session, role_1):
    UserStore().create_role(state, 'my_role', role_1)
    UserStore().delete_role(state, 'my_role')


def test__delete_role__can_delete_role_when_assigned(state, session, role_1, db_user_1, db_user_2):
    UserStore().create_role(state, 'my_role', role_1)
    UserStore().assign_user_role(state, db_user_1, 'my_role')
    UserStore().assign_user_role(state, db_user_2, 'my_role')
    UserStore().delete_role(state, 'my_role')
    with state.Session.begin() as session:
        db_user1 = session.execute(select(User).where(User.id == db_user_1.id)).one()[0]
        db_user2 = session.execute(select(User).where(User.id == db_user_2.id)).one()[0]
        assert db_user1.role is None
        assert db_user2.role is None


def test__delete_role__cant_delete_non_existing(state, session):
    with pytest.raises(NoRoleWithName):
        UserStore().delete_role(state, 'my_role')


def test__assign_user_role__can_assign_user(state, session, db_user_1, role_1):
    UserStore().create_role(state, 'my_role', role_1)
    UserStore().assign_user_role(state, db_user_1, 'my_role')


def test__assign_user_role__can_assign_user_many_times(state, session, db_user_1, role_1, role_2):
    UserStore().create_role(state, 'my_role', role_1)
    expected_role = UserStore().create_role(state, 'my_role2', role_2)
    UserStore().assign_user_role(state, db_user_1, 'my_role')
    UserStore().assign_user_role(state, db_user_1, 'my_role2')

    with state.Session.begin() as session:
        query = select(User).where(User.id == db_user_1.id)
        db_user = session.execute(query).one()[0]
        assert db_user.role == expected_role.id


def test__assign_user_role__cant_assign_invalid_role(state, session, db_user_1):
    with pytest.raises(NoRoleWithName):
        UserStore().assign_user_role(state, db_user_1, 'my_role')


def test__get_users_role__expected_role_returned(state, session, db_user_1, role_1):
    role = UserStore().create_role(state, 'role', role_1)
    UserStore().assign_user_role(state, db_user_1, 'role')
    returned_role = UserStore().get_users_role(state, db_user_1)
    assert role.into_roles().as_dict() == returned_role.as_dict()


def test__get_users_role__none_returned_if_no_role(state, session, db_user_1):
    assert UserStore().get_users_role(state, db_user_1) is None


def test__edit_role__does_not_change_other_roles(state, session, role_1, role_2):
    UserStore().create_role(state, 'role_a', role_1)
    role_b = UserStore().create_role(state, 'role_b', role_2)
    UserStore().edit_role(state, 'role_a', role_2)
    with state.Session.begin() as session:
        query = select(Role).where(Role.name == 'role_b')
        db_role_b = session.execute(query).one()[0]
        assert db_role_b.into_roles().as_dict() == role_b.into_roles().as_dict()


def test__get_all_roles__success(state, session, role_1, role_2, db_role_1, db_role_2, role_name_1, role_name_2):
    roles = UserStore().get_all_roles(state)
    assert len(roles) == 2
    assert roles[0].into_roles().as_dict() == role_1.as_dict()
    assert roles[0].name == role_name_1
    assert roles[1].into_roles().as_dict() == role_2.as_dict()
    assert roles[1].name == role_name_2


def test__get_all_roles__no_roles_empty(state, session):
    roles = UserStore().get_all_roles(state)
    assert len(roles) == 0


def test__get_all_users_paginated__empty_database_returns_empty_list(state, session):
    """Test that pagination works with no users in database"""
    result = UserStore().get_all_users_paginated(state, page=1, page_size=50)
    assert result['users'] == []
    assert result['total'] == 0
    assert result['page'] == 1
    assert result['page_size'] == 50
    assert result['total_pages'] == 0


def test__get_all_users_paginated__single_user_returns_correct_data(state, session, db_user_1):
    """Test that single user is returned with correct structure"""
    result = UserStore().get_all_users_paginated(state, page=1, page_size=50)
    assert len(result['users']) == 1
    assert result['total'] == 1
    assert result['total_pages'] == 1

    user = result['users'][0]
    assert user['id'] == db_user_1.id
    assert user['uuid'] == str(db_user_1.uuid)
    assert user['creation_date'] == db_user_1.creation_date.isoformat()
    assert user['role'] is None
    assert user['groups'] == []
    assert user['connected_apps']['discord'] is False
    assert user['connected_apps']['bot'] is False


def test__get_all_users_paginated__multiple_users_returns_all(state, session, db_user_1, db_user_2):
    """Test that multiple users are returned"""
    result = UserStore().get_all_users_paginated(state, page=1, page_size=50)
    assert len(result['users']) == 2
    assert result['total'] == 2
    assert result['total_pages'] == 1


def test__get_all_users_paginated__user_with_role_returns_role_name(state, session, db_user_1, role_1, role_name_1):
    """Test that user's role name is included"""
    UserStore().create_role(state, role_name_1, role_1)
    UserStore().assign_user_role(state, db_user_1, role_name_1)

    result = UserStore().get_all_users_paginated(state, page=1, page_size=50)
    user = result['users'][0]
    assert user['role'] == role_name_1


def test__get_all_users_paginated__user_with_groups_returns_group_names(state, session, db_user_1, db_group_1, db_group_2):
    """Test that user's group names are included"""
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    GroupStore().assign_user_to_group(state, db_user_1, db_group_2)

    result = UserStore().get_all_users_paginated(state, page=1, page_size=50)
    user = result['users'][0]
    assert set(user['groups']) == {db_group_1.name, db_group_2.name}


def test__get_all_users_paginated__user_with_discord_shows_connected(state, session, db_user_1, db_discord_user_1):
    """Test that Discord connection is shown"""
    result = UserStore().get_all_users_paginated(state, page=1, page_size=50)
    user = result['users'][0]
    assert user['connected_apps']['discord'] is True
    assert user['connected_apps']['bot'] is False


def test__get_all_users_paginated__user_with_bot_shows_connected(state, session, db_user_1, db_bot_user_1):
    """Test that bot connection is shown"""
    result = UserStore().get_all_users_paginated(state, page=1, page_size=50)
    user = result['users'][0]
    assert user['connected_apps']['discord'] is False
    assert user['connected_apps']['bot'] is True


def test__get_all_users_paginated__user_with_both_connections_shows_both(
    state, session, db_user_1, db_discord_user_1, db_bot_user_1
):
    """Test that both connections are shown"""
    result = UserStore().get_all_users_paginated(state, page=1, page_size=50)
    user = result['users'][0]
    assert user['connected_apps']['discord'] is True
    assert user['connected_apps']['bot'] is True


def test__get_all_users_paginated__pagination_first_page(state, session):
    """Test first page of paginated results"""
    # Create 3 users
    UserStore().create_user(state)
    UserStore().create_user(state)
    UserStore().create_user(state)

    result = UserStore().get_all_users_paginated(state, page=1, page_size=2)
    assert len(result['users']) == 2
    assert result['total'] == 3
    assert result['page'] == 1
    assert result['page_size'] == 2
    assert result['total_pages'] == 2


def test__get_all_users_paginated__pagination_second_page(state, session):
    """Test second page of paginated results"""
    # Create 3 users
    UserStore().create_user(state)
    UserStore().create_user(state)
    UserStore().create_user(state)

    result = UserStore().get_all_users_paginated(state, page=2, page_size=2)
    assert len(result['users']) == 1
    assert result['total'] == 3
    assert result['page'] == 2
    assert result['total_pages'] == 2


def test__get_all_users_paginated__pagination_beyond_last_page_returns_empty(state, session, db_user_1):
    """Test requesting page beyond available data"""
    result = UserStore().get_all_users_paginated(state, page=5, page_size=50)
    assert len(result['users']) == 0
    assert result['total'] == 1
    assert result['page'] == 5
    assert result['total_pages'] == 1


def test__get_all_users_paginated__custom_page_size(state, session):
    """Test custom page size"""
    # Create 10 users
    for _ in range(10):
        UserStore().create_user(state)

    result = UserStore().get_all_users_paginated(state, page=1, page_size=3)
    assert len(result['users']) == 3
    assert result['total'] == 10
    assert result['total_pages'] == 4


def test__get_all_users_paginated__total_pages_calculation_exact_division(state, session):
    """Test total pages when users divide evenly into page size"""
    # Create 6 users
    for _ in range(6):
        UserStore().create_user(state)

    result = UserStore().get_all_users_paginated(state, page=1, page_size=3)
    assert result['total_pages'] == 2


def test__get_all_users_paginated__total_pages_calculation_with_remainder(state, session):
    """Test total pages when users don't divide evenly"""
    # Create 7 users
    for _ in range(7):
        UserStore().create_user(state)

    result = UserStore().get_all_users_paginated(state, page=1, page_size=3)
    assert result['total_pages'] == 3


def test__get_all_users_paginated__users_ordered_consistently(state, session):
    """Test that users are returned in consistent order across pages"""
    # Create 5 users
    users = []
    for _ in range(5):
        users.append(UserStore().create_user(state))

    page1 = UserStore().get_all_users_paginated(state, page=1, page_size=3)
    page2 = UserStore().get_all_users_paginated(state, page=2, page_size=3)

    # Should have no overlapping user IDs
    page1_ids = {user['id'] for user in page1['users']}
    page2_ids = {user['id'] for user in page2['users']}
    assert len(page1_ids & page2_ids) == 0
