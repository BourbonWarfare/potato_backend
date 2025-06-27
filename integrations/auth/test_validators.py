# ruff: noqa: F811, F401

import pytest

from bw.auth.validators import validate_user_has_role, validate_session, validate_user_has_permissions
from bw.auth.roles import Roles
from bw.auth.permissions import Permissions
from bw.auth.user import UserStore
from bw.auth.group import GroupStore
from integrations.auth.fixtures import (
    state,
    session,
    db_user_1,
    db_session_1,
    db_expired_session_1,
    role_1,
    token_1,
    expire_invalid,
    role_2,
    permission_1,
    permission_2,
    db_permission_1,
    db_permission_2,
    db_group_1,
    db_group_2,
    permission_name_1,
    permission_name_2,
    group_name_1,
    group_name_2,
)
from bw.error import SessionInvalid, NotEnoughPermissions


def test__validate_session__active_session_passes(state, session, db_session_1):
    validate_session(state, db_session_1.token)


def test__validate_session__inactive_session_passes(state, session, db_expired_session_1):
    with pytest.raises(SessionInvalid):
        validate_session(state, db_expired_session_1.token)


def test__validate_user_has_roles__user_with_roles_passes(state, session, db_session_1, db_user_1, role_1):
    UserStore().create_role(state, 'role', role_1)
    UserStore().assign_user_role(state, db_user_1, 'role')
    validate_user_has_role(state, db_session_1.token, role_1)


def test__validate_user_has_roles__user_without_roles_fails(state, session, db_session_1, db_user_1, role_1, role_2):
    with pytest.raises(NotEnoughPermissions):
        validate_user_has_role(state, db_session_1.token, role_1)

    UserStore().create_role(state, 'role', role_2)
    UserStore().assign_user_role(state, db_user_1, 'role')
    with pytest.raises(NotEnoughPermissions):
        validate_user_has_role(state, db_session_1.token, role_1)


def test__validate_user_has_roles__user_with_superset_passes(state, session, db_session_1, db_user_1, role_1, role_2):
    UserStore().create_role(state, 'role', Roles.from_many(role_1, role_2))
    UserStore().assign_user_role(state, db_user_1, 'role')
    validate_user_has_role(state, db_session_1.token, role_1)


def test__validate_user_has_perms__user_with_perms_passes(state, session, db_session_1, db_user_1, db_group_1, permission_1):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    validate_user_has_permissions(state, db_session_1.token, permission_1)


def test__validate_user_has_perms__user_without_perms_fails(state, session, db_session_1, db_user_1, permission_1, db_group_2):
    with pytest.raises(NotEnoughPermissions):
        validate_user_has_permissions(state, db_session_1.token, permission_1)

    GroupStore().assign_user_to_group(state, db_user_1, db_group_2)
    with pytest.raises(NotEnoughPermissions):
        validate_user_has_permissions(state, db_session_1.token, permission_1)


def test__validate_user_has_perms__user_with_superset_passes(
    state, session, db_session_1, db_user_1, db_group_1, permission_1, db_group_2, permission_2
):
    GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
    GroupStore().assign_user_to_group(state, db_user_1, db_group_2)
    validate_user_has_permissions(state, db_session_1.token, permission_1)
    validate_user_has_permissions(state, db_session_1.token, permission_2)
