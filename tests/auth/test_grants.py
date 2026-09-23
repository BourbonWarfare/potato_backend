import pytest

from bw.auth.grants import InvalidGrant, UnknownGrant
from bw.auth.permissions import Permissions
from bw.auth.roles import Roles


def test__roles__auto_namespace_known_code_grants_case_insensitively():
    roles = Roles(['CAN_CREATE_ROLE', 'role:CAN_MANAGE_SERVER'])

    assert roles.has('can_create_role')
    assert roles.has('ROLE:can_MANAGE_server')
    assert Roles.can_create_role == 'role:can_create_role'


def test__permissions__auto_namespace_new_grants_without_schema_changes():
    permissions = Permissions(['Can_Publish_Mission', Permissions.can_test_mission])

    assert permissions.as_list() == ['group:can_publish_mission', 'group:can_test_mission']
    assert permissions.has('CAN_PUBLISH_MISSION')
    assert permissions.has('GROUP:CAN_PUBLISH_MISSION')


def test__roles__reject_group_grants():
    with pytest.raises(InvalidGrant):
        Roles([Permissions.can_test_mission])


def test__roles__reject_unknown_role_grants():
    with pytest.raises(UnknownGrant):
        Roles(['some_new_runtime_role'])


def test__permissions__reject_role_grants():
    with pytest.raises(InvalidGrant):
        Permissions([Roles.can_create_group])


def test__from_keys__rejects_legacy_boolean_flags():
    with pytest.raises(TypeError):
        Roles.from_keys(can_create_group=True)


def test__from_many__combines_grants_case_insensitively():
    combined = Permissions.from_many(Permissions(['CAN_UPLOAD_MISSION']), Permissions(['group:can_test_mission']))

    assert combined.as_list() == ['group:can_test_mission', 'group:can_upload_mission']
