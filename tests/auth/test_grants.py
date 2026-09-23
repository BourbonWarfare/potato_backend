from bw.auth.permissions import Permissions
from bw.auth.roles import Roles


def test__roles__are_case_insensitive_string_grants():
    roles = Roles(['CAN_CREATE_ROLE', 'custom.Permission'])

    assert roles.has('can_create_role')
    assert roles.has('can_CREATE_role')
    assert roles.has('CUSTOM.permission')
    assert Roles.can_create_role == 'can_create_role'
    assert roles.can_create_role is True


def test__permissions__support_new_grants_without_schema_changes():
    permissions = Permissions(['Can_Publish_Mission', Permissions.can_test_mission])

    assert permissions.as_list() == ['can_publish_mission', 'can_test_mission']
    assert permissions.has('CAN_PUBLISH_MISSION')
    assert permissions.can_test_mission is True


def test__grants__legacy_boolean_kwargs_still_create_string_grants():
    roles = Roles(can_create_group=True, can_create_role=False)

    assert roles.as_csv() == 'can_create_group'
    assert roles.as_dict() == {'can_create_group': True}
    assert roles.can_create_group is True
    assert roles.can_create_role is False


def test__from_many__combines_grants_case_insensitively():
    combined = Permissions.from_many(Permissions(['CAN_UPLOAD_MISSION']), Permissions(['can_test_mission']))

    assert combined.as_list() == ['can_test_mission', 'can_upload_mission']
