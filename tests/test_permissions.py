import pytest

from bw.auth.permissions import Permissions


@pytest.fixture
def permission_1():
    return Permissions(can_upload_mission=True, can_test_mission=False)


@pytest.fixture
def permission_2():
    return Permissions(can_upload_mission=False, can_test_mission=True)


def test__permissions__correct_dict_return(permission_1):
    test_dict = permission_1.as_dict()
    assert all([test_dict[k] == getattr(permission_1, k) for k in permission_1.__slots__])


def test__permissions__combine_from_many_identity(permission_1):
    combined = Permissions.from_many(permission_1)

    assert combined.as_dict() == permission_1.as_dict()


def test__permissions__combine_from_many(permission_1, permission_2):
    combined = Permissions.from_many(permission_1, permission_2)

    assert combined.can_upload_mission
    assert combined.can_test_mission
