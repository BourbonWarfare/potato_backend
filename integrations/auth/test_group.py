# ruff: noqa: F811, F401

import pytest

from sqlalchemy import select

from bw.auth.permissions import Permissions
from bw.error import GroupPermissionCreationFailed, GroupCreationFailed, NoGroupPermissionWithCredentials, GroupAssignmentFailed
from bw.models.auth import GroupPermission, Group, UserGroup
from bw.auth.group import GroupStore
from integrations.auth.fixtures import (
    state,
    session,
    db_user_1,
    permission_1,
    db_permission_1,
    permission_name_1,
    permission_name_2,
    permission_2,
    db_group_1,
    db_user_1,
    group_name_1,
    group_name_2,
    db_user_2,
    db_group_2,
    db_permission_2,
    db_permission_3,
    permission_3,
    permission_name_3,
    db_group_3,
    group_name_3,
)


def test__create_permission__can_create_no_throw(state, session, permission_1):
    db_permission = GroupStore().create_permission(state, 'my permission', permission_1)

    assert db_permission.name == 'my permission'
    assert db_permission.into_permissions().as_dict() == permission_1.as_dict()
    with state.Session.begin() as session:
        query = select(GroupPermission).where(GroupPermission.id == db_permission.id)
        row = session.execute(query).first()
        assert row is not None


def test__create_permission__can_only_create_single_name(state, session, permission_1):
    GroupStore().create_permission(state, 'my permission', permission_1)
    with pytest.raises(GroupPermissionCreationFailed):
        GroupStore().create_permission(state, 'my permission', permission_1)


def test__create_group__can_create_no_throw(state, session, db_permission_1):
    group = GroupStore().create_group(state, 'my group', db_permission_1.name)
    assert group.name == 'my group'
    with state.Session.begin() as session:
        query = select(Group).where(Group.id == group.id)
        row = session.execute(query).first()
        assert row is not None


def test__create_group__can_only_create_single(state, session, db_permission_1):
    GroupStore().create_group(state, 'my group', db_permission_1.name)
    with pytest.raises(GroupCreationFailed):
        GroupStore().create_group(state, 'my group', db_permission_1.name)


def test__create_group__cant_add_invalid_permission(state, session):
    with pytest.raises(GroupCreationFailed):
        GroupStore().create_group(state, 'my group', 'johnny')


def test__get_permission__can_get_valid_permission(state, session, db_permission_1):
    permission = GroupStore().get_permission(state, db_permission_1.name)
    assert permission.id == db_permission_1.id
    assert permission.name == db_permission_1.name
    assert permission.into_permissions().as_dict() == db_permission_1.into_permissions().as_dict()


def test__get_permission__cant_get_invalid_permission(state, session, db_permission_1, permission_name_2):
    with pytest.raises(NoGroupPermissionWithCredentials):
        GroupStore().get_permission(state, permission_name_2)


def test__edit_permission__can_edit_permission(state, session, db_permission_1, permission_2):
    new_permission = GroupStore().edit_permission(state, db_permission_1.name, permission_2)
    assert new_permission.id == db_permission_1.id
    assert new_permission.name == db_permission_1.name
    assert new_permission.into_permissions().as_dict() == permission_2.as_dict()
    with state.Session.begin() as session:
        query = select(GroupPermission).where(GroupPermission.id == new_permission.id)
        row = session.execute(query).first()
        assert row is not None
        assert row[0].id == db_permission_1.id
        assert row[0].into_permissions().as_dict() == permission_2.as_dict()


def test__edit_permission__cant_edit_nonexistant_permission(state, session, db_permission_1, permission_2, permission_name_2):
    with pytest.raises(NoGroupPermissionWithCredentials):
        GroupStore().edit_permission(state, permission_name_2, permission_2)


def test__assign_user_to_group__can_assign(state, session, db_group_1, db_user_1):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    with state.Session.begin() as session:
        query = select(UserGroup).where(UserGroup.user_id == db_user_1.id).where(UserGroup.group_id == db_group_1.id)
        row = session.execute(query).first()
        assert row is not None


def test__assign_user_to_group__can_assign_only_once(state, session, db_group_1, db_user_1):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    with pytest.raises(GroupAssignmentFailed):
        GroupStore().assign_user_to_group(state, db_user_1, db_group_1)


def test__assign_user_to_group__can_assign_many_users_to_group(state, session, db_group_1, db_user_1, db_user_2):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    GroupStore().assign_user_to_group(state, db_user_2, db_group_1)
    with state.Session.begin() as session:
        query = select(UserGroup).where(UserGroup.user_id == db_user_1.id).where(UserGroup.group_id == db_group_1.id)
        row = session.execute(query).first()
        assert row is not None

        query = select(UserGroup).where(UserGroup.user_id == db_user_2.id).where(UserGroup.group_id == db_group_1.id)
        row = session.execute(query).first()
        assert row is not None


def test__assign_user_to_group__can_assign_user_to_many_groups(state, session, db_group_1, db_user_1, db_group_2):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    GroupStore().assign_user_to_group(state, db_user_1, db_group_2)
    with state.Session.begin() as session:
        query = select(UserGroup).where(UserGroup.user_id == db_user_1.id).where(UserGroup.group_id == db_group_1.id)
        row = session.execute(query).first()
        assert row is not None

        query = select(UserGroup).where(UserGroup.user_id == db_user_1.id).where(UserGroup.group_id == db_group_2.id)
        row = session.execute(query).first()
        assert row is not None


def test__remove_user_from_group__can_remove_user(state, session, db_group_1, db_user_1):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    with state.Session.begin() as session:
        query = select(UserGroup).where(UserGroup.user_id == db_user_1.id).where(UserGroup.group_id == db_group_1.id)
        row = session.execute(query).first()
        assert row is not None

    GroupStore().remove_user_from_group(state, db_user_1, db_group_1)
    with state.Session.begin() as session:
        query = select(UserGroup).where(UserGroup.user_id == db_user_1.id).where(UserGroup.group_id == db_group_1.id)
        row = session.execute(query).first()
        assert row is None


def test__remove_user_from_group__nothing_if_cant_remove_user(state, session, db_group_1, db_user_1):
    GroupStore().remove_user_from_group(state, db_user_1, db_group_1)


def test__delete_group__can_delete_empty(state, session, db_group_1):
    GroupStore().delete_group(state, db_group_1.name)


def test__delete_group__can_delete_with_user(state, session, db_group_1, db_user_1):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    GroupStore().delete_group(state, db_group_1.name)


def test__delete_group__can_delete_with_users(state, session, db_group_1, db_user_1, db_user_2):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    GroupStore().assign_user_to_group(state, db_user_2, db_group_1)
    GroupStore().delete_group(state, db_group_1.name)


def test__delete_group__can_delete_with_user_only_one_group(state, session, db_group_1, db_user_1, db_group_2):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    GroupStore().assign_user_to_group(state, db_user_1, db_group_2)
    GroupStore().delete_group(state, db_group_1.name)

    with state.Session.begin() as session:
        query = select(UserGroup).where(UserGroup.user_id == db_user_1.id).where(UserGroup.group_id == db_group_2.id)
        row = session.execute(query).first()
        assert row is not None
        assert len(row) == 1


def test__get_all_permissions_user_has__no_permissions_if_not_in_group(state, session, db_user_1):
    permissions = GroupStore().get_all_permissions_user_has(state, db_user_1)
    assert not any(permissions.as_dict().values())


def test__get_all_permissions_user_has__user_has_expected_permissions_from_single_group(
    state, session, db_user_1, db_group_1, db_permission_1
):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    permissions = GroupStore().get_all_permissions_user_has(state, db_user_1)
    assert db_permission_1.into_permissions().as_dict() == permissions.as_dict()


def test__get_all_permissions_user_has__user_has_expected_permissions_from_single_group_with_many(
    state, session, db_user_1, db_group_1, db_permission_1, db_group_2
):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    permissions = GroupStore().get_all_permissions_user_has(state, db_user_1)
    assert db_permission_1.into_permissions().as_dict() == permissions.as_dict()


def test__get_all_permissions_user_has__user_has_expected_permissions_from_many_groups(
    state, session, db_user_1, db_group_1, db_permission_1, db_group_2, db_permission_2
):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    GroupStore().assign_user_to_group(state, db_user_1, db_group_2)
    permissions = GroupStore().get_all_permissions_user_has(state, db_user_1)

    combined = Permissions.from_many(db_permission_1.into_permissions(), db_permission_2.into_permissions())
    assert combined.as_dict() == permissions.as_dict()


def test__get_all_permissions_user_has__user_has_expected_permissions_from_many_groups_with_many(
    state,
    session,
    db_user_1,
    db_group_1,
    db_permission_1,
    db_permission_2,
    db_group_2,
    db_permission_3,
    db_group_3,
    permission_3,
    permission_name_3,
):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_3)
    GroupStore().assign_user_to_group(state, db_user_1, db_group_2)
    permissions = GroupStore().get_all_permissions_user_has(state, db_user_1)

    combined = Permissions.from_many(db_permission_2.into_permissions(), db_permission_3.into_permissions())
    assert combined.as_dict() == permissions.as_dict()
