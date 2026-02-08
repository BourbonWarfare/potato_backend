# ruff: noqa: F811, F401

import pytest

from sqlalchemy import select

from bw.auth.permissions import Permissions
from bw.error import (
    GroupPermissionCreationFailed,
    GroupCreationFailed,
    NoGroupPermissionWithCredentials,
    GroupAssignmentFailed,
    NoGroupWithName,
)
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


def test__remove_user_from_group__no_error_if_user_not_in_group(state, session, db_group_1, db_user_2):
    GroupStore().remove_user_from_group(state, db_user_2, db_group_1)
    with state.Session.begin() as session:
        query = select(UserGroup).where(UserGroup.user_id == db_user_2.id).where(UserGroup.group_id == db_group_1.id)
        row = session.execute(query).first()
        assert row is None


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


def test__delete_group__no_error_if_group_does_not_exist(state, session, group_name_1):
    GroupStore().delete_group(state, group_name_1)


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


def test__get_group__can_get_existing_group(state, session, db_group_1):
    group = GroupStore().get_group(state, db_group_1.name)
    assert group.id == db_group_1.id
    assert group.name == db_group_1.name


def test__get_group__raises_on_nonexistent_group(state, session, group_name_1):
    with pytest.raises(NoGroupWithName):
        GroupStore().get_group(state, group_name_1)


def test__get_user_groups__returns_all_groups(state, session, db_user_1, db_group_1, db_group_2, db_group_3):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    GroupStore().assign_user_to_group(state, db_user_1, db_group_2)
    groups = GroupStore().get_user_groups(state, db_user_1)
    assert {group.id for group in groups} == {db_group_1.id, db_group_2.id}


def test__get_all_permissions__empty_database_returns_empty_list(state, session):
    """Test that get_all_permissions returns empty list when no permissions exist"""
    permissions = GroupStore().get_all_permissions(state)
    assert len(permissions) == 0


def test__get_all_permissions__single_permission_returns_correctly(state, session, db_permission_1):
    """Test that single permission is returned"""
    permissions = GroupStore().get_all_permissions(state)
    assert len(permissions) == 1
    assert permissions[0].id == db_permission_1.id
    assert permissions[0].name == db_permission_1.name
    assert permissions[0].into_permissions().as_dict() == db_permission_1.into_permissions().as_dict()


def test__get_all_permissions__multiple_permissions_returns_all(
    state, session, db_permission_1, db_permission_2, db_permission_3
):
    """Test that all permissions are returned"""
    permissions = GroupStore().get_all_permissions(state)
    assert len(permissions) == 3

    permission_ids = {perm.id for perm in permissions}
    assert permission_ids == {db_permission_1.id, db_permission_2.id, db_permission_3.id}


def test__get_all_permissions__returns_correct_permission_details(
    state, session, db_permission_1, permission_1, permission_name_1
):
    """Test that permission details are correct"""
    permissions = GroupStore().get_all_permissions(state)
    perm = permissions[0]

    assert perm.name == permission_name_1
    assert perm.into_permissions().as_dict() == permission_1.as_dict()


def test__get_all_permissions__permissions_are_detached_from_session(state, session, db_permission_1):
    """Test that returned permissions can be used outside of session context"""
    permissions = GroupStore().get_all_permissions(state)
    # Should be able to access attributes without session
    assert permissions[0].name == db_permission_1.name
    assert permissions[0].id == db_permission_1.id


# Tests for get_all_groups


def test__get_all_groups__empty_database_returns_empty_list(state, session):
    """Test that get_all_groups returns empty list when no groups exist"""
    groups = GroupStore().get_all_groups(state)
    assert len(groups) == 0


def test__get_all_groups__single_group_returns_correctly(state, session, db_group_1):
    """Test that single group is returned"""
    groups = GroupStore().get_all_groups(state)
    assert len(groups) == 1
    assert groups[0].id == db_group_1.id
    assert groups[0].name == db_group_1.name
    assert groups[0].permissions == db_group_1.permissions


def test__get_all_groups__multiple_groups_returns_all(state, session, db_group_1, db_group_2, db_group_3):
    """Test that all groups are returned"""
    groups = GroupStore().get_all_groups(state)
    assert len(groups) == 3

    group_ids = {group.id for group in groups}
    assert group_ids == {db_group_1.id, db_group_2.id, db_group_3.id}


def test__get_all_groups__returns_correct_group_details(state, session, db_group_1, group_name_1, db_permission_1):
    """Test that group details are correct"""
    groups = GroupStore().get_all_groups(state)
    group = groups[0]

    assert group.name == group_name_1
    assert group.permissions == db_permission_1.id


def test__get_all_groups__groups_are_detached_from_session(state, session, db_group_1):
    """Test that returned groups can be used outside of session context"""
    groups = GroupStore().get_all_groups(state)
    # Should be able to access attributes without session
    assert groups[0].name == db_group_1.name
    assert groups[0].id == db_group_1.id
    assert groups[0].permissions == db_group_1.permissions


def test__get_all_groups__groups_with_users_still_returned(state, session, db_group_1, db_user_1):
    """Test that groups with assigned users are still returned"""
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)

    groups = GroupStore().get_all_groups(state)
    assert len(groups) == 1
    assert groups[0].id == db_group_1.id


# Tests for delete_permission


def test__delete_permission__can_delete_existing_permission(state, session, db_permission_1):
    """Test that existing permission can be deleted"""
    GroupStore().delete_permission(state, db_permission_1.name)

    # Verify it's gone
    with pytest.raises(NoGroupPermissionWithCredentials):
        GroupStore().get_permission(state, db_permission_1.name)


def test__delete_permission__raises_on_nonexistent_permission(state, session, permission_name_1):
    """Test that deleting non-existent permission raises error"""
    with pytest.raises(NoGroupPermissionWithCredentials):
        GroupStore().delete_permission(state, permission_name_1)


def test__delete_permission__can_delete_multiple_permissions(state, session, db_permission_1, db_permission_2, db_permission_3):
    """Test that multiple permissions can be deleted independently"""
    GroupStore().delete_permission(state, db_permission_1.name)
    GroupStore().delete_permission(state, db_permission_2.name)

    # permission_3 should still exist
    perm = GroupStore().get_permission(state, db_permission_3.name)
    assert perm.id == db_permission_3.id


def test__delete_permission__delete_does_not_affect_other_permissions(state, session, db_permission_1, db_permission_2):
    """Test that deleting one permission doesn't affect others"""
    GroupStore().delete_permission(state, db_permission_1.name)

    # permission_2 should still exist with correct data
    perm = GroupStore().get_permission(state, db_permission_2.name)
    assert perm.id == db_permission_2.id
    assert perm.name == db_permission_2.name


def test__delete_permission__empty_database_after_all_deleted(state, session, db_permission_1, db_permission_2, db_permission_3):
    """Test that database is empty after all permissions deleted"""
    GroupStore().delete_permission(state, db_permission_1.name)
    GroupStore().delete_permission(state, db_permission_2.name)
    GroupStore().delete_permission(state, db_permission_3.name)

    permissions = GroupStore().get_all_permissions(state)
    assert len(permissions) == 0


def test__delete_permission__cannot_delete_same_permission_twice(state, session, db_permission_1):
    """Test that deleting the same permission twice raises error on second attempt"""
    GroupStore().delete_permission(state, db_permission_1.name)

    with pytest.raises(NoGroupPermissionWithCredentials):
        GroupStore().delete_permission(state, db_permission_1.name)
