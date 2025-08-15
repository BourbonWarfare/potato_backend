import pytest

from bw.auth import validators
from bw.error import NonLocalIpAccessingLocalOnlyAddress, SessionExpired, NotEnoughPermissions


def test__validate_local__non_local_ip_raises():
    with pytest.raises(NonLocalIpAccessingLocalOnlyAddress):
        validators.validate_local('8.8.8.8')


def test__validate_local__local_ip_fine():
    validators.validate_local('0.0.0.0')
    validators.validate_local('10.0.0.1')
    validators.validate_local('127.0.0.1')
    validators.validate_local('172.16.5.1')
    validators.validate_local('192.0.0.1')
    validators.validate_local('192.168.56.1')


def test__validate_session__invalid_session_raises(mocker):
    mocker.patch('bw.auth.api.AuthApi.is_session_active', return_value=False)

    with pytest.raises(SessionExpired):
        validators.validate_session(None, 'token')  # state not needed; we mock it


def test__validate_session__valid_session_passes(mocker):
    mocker.patch('bw.auth.api.AuthApi.is_session_active', return_value=True)
    validators.validate_session(None, 'token')  # state not needed; we mock it


def test__validate_user_has_role__no_role_raises(mocker):
    mocker.patch('bw.auth.api.AuthApi.does_user_have_roles', return_value=False)

    with pytest.raises(NotEnoughPermissions):
        validators.validate_user_has_role(None, 'token', None)  # state not needed; we mock it


def test__validate_user_has_role__valid_session_passes(mocker):
    mocker.patch('bw.auth.api.AuthApi.does_user_have_roles', return_value=True)
    validators.validate_user_has_role(None, 'token', None)  # state not needed; we mock it
