import pytest
import unittest
from bw.auth.decorators import require_local, require_session, require_group_permission, require_user_role
from bw.error.auth import NonLocalIpAccessingLocalOnlyAddress, CannotDetermineSession, SessionExpired, NotEnoughPermissions
from bw.auth.permissions import Permissions
from bw.auth.roles import Roles


class MockUser:
    def __init__(self):
        self.id = 533
        self.data = 12345


@pytest.fixture
def mock_session_user() -> MockUser:
    return MockUser()


class TestRequireLocal:
    def test__require_local__sync__local_ip_succeeds(self):
        called = False

        @require_local
        def tester():
            nonlocal called
            called = True

        with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
            mock_request.remote_addr = '127.0.0.1'
            tester()
        assert called

    def test__require_local__sync__remote_ip_fails(self):
        called = False

        @require_local
        def tester():
            nonlocal called
            called = True

        with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
            mock_request.remote_addr = '8.8.8.8'
            with pytest.raises(NonLocalIpAccessingLocalOnlyAddress):
                tester()
        assert not called

    def test__require_local__sync__arguments_passed(self):
        @require_local
        def tester(arg1: int, arg2: str):
            assert isinstance(arg1, int)
            assert arg1 == 42

            assert isinstance(arg2, str)
            assert arg2 == 'test'

        with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
            mock_request.remote_addr = '127.0.0.1'
            tester(42, arg2='test')

    @pytest.mark.asyncio
    async def test__require_local__async__local_ip_succeeds(self):
        called = False

        @require_local
        async def tester():
            nonlocal called
            called = True

        with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
            mock_request.remote_addr = '127.0.0.1'
            await tester()
        assert called

    @pytest.mark.asyncio
    async def test__require_local__async__remote_ip_fails(self):
        called = False

        @require_local
        async def tester():
            nonlocal called
            called = True

        with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
            mock_request.remote_addr = '8.8.8.8'
            with pytest.raises(NonLocalIpAccessingLocalOnlyAddress):
                await tester()
        assert not called

    @pytest.mark.asyncio
    async def test__require_local__async__arguments_passed(self):
        @require_local
        async def tester(arg1: int, arg2: str):
            assert isinstance(arg1, int)
            assert arg1 == 42

            assert isinstance(arg2, str)
            assert arg2 == 'test'

        with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
            mock_request.remote_addr = '127.0.0.1'
            await tester(42, arg2='test')


class TestRequireSession:
    def test__require_session__sync__with_header_succeeds(self):
        called = False

        @require_session
        def tester(session_user):
            nonlocal called
            called = True
            assert session_user == 123456

        with unittest.mock.patch('bw.auth.decorators.validate_session') as mock_validator:
            with unittest.mock.patch(
                'bw.auth.decorators.SessionStore.get_user_from_session_token', return_value=123456
            ) as mock_get_session_user:
                with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
                    mock_request.headers = {'Authorization': 'Bearer valid_token'}
                    tester()
        assert mock_validator.called
        assert mock_get_session_user.called
        assert called

    def test__require_session__sync__without_header_fails(self):
        called = False

        @require_session
        def tester(session_user):
            nonlocal called
            called = True
            assert session_user == 123456

        with unittest.mock.patch('bw.auth.decorators.validate_session') as mock_validator:
            with unittest.mock.patch(
                'bw.auth.decorators.SessionStore.get_user_from_session_token', return_value=123456
            ) as mock_get_session_user:
                with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
                    mock_request.headers = {}
                    with pytest.raises(CannotDetermineSession):
                        tester()
        assert not mock_validator.called
        assert not mock_get_session_user.called
        assert not called

    def test__require_session__sync__invalid_header_fails(self):
        called = False

        @require_session
        def tester(session_user):
            nonlocal called
            called = True
            assert session_user == 123456

        with unittest.mock.patch('bw.auth.decorators.validate_session') as mock_validator:
            with unittest.mock.patch(
                'bw.auth.decorators.SessionStore.get_user_from_session_token', return_value=123456
            ) as mock_get_session_user:
                with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
                    mock_request.headers = {'Authorization': 'Meercat valid_token'}
                    with pytest.raises(CannotDetermineSession):
                        tester()
        assert not mock_validator.called
        assert not mock_get_session_user.called
        assert not called

    def test__require_session__sync__validate_session_raises(self):
        called = False

        @require_session
        def tester(session_user):
            nonlocal called
            called = True
            assert session_user == 123456

        with unittest.mock.patch('bw.auth.decorators.validate_session', side_effect=SessionExpired) as mock_validator:
            with unittest.mock.patch(
                'bw.auth.decorators.SessionStore.get_user_from_session_token', return_value=123456
            ) as mock_get_session_user:
                with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
                    mock_request.headers = {'Authorization': 'Bearer valid_token'}
                    with pytest.raises(SessionExpired):
                        tester()
        assert mock_validator.called
        assert not mock_get_session_user.called
        assert not called

    def test__require_session__sync__get_user_raises(self):
        called = False

        @require_session
        def tester(session_user):
            nonlocal called
            called = True
            assert session_user == 123456

        with unittest.mock.patch('bw.auth.decorators.validate_session') as mock_validator:
            with unittest.mock.patch(
                'bw.auth.decorators.SessionStore.get_user_from_session_token', side_effect=SessionExpired
            ) as mock_get_session_user:
                with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
                    mock_request.headers = {'Authorization': 'Bearer valid_token'}
                    with pytest.raises(SessionExpired):
                        tester()
        assert mock_validator.called
        assert mock_get_session_user.called
        assert not called

    @pytest.mark.asyncio
    async def test__require_session__async__with_header_succeeds(self):
        called = False

        @require_session
        async def tester(session_user):
            nonlocal called
            called = True
            assert session_user == 123456

        with unittest.mock.patch('bw.auth.decorators.validate_session') as mock_validator:
            with unittest.mock.patch(
                'bw.auth.decorators.SessionStore.get_user_from_session_token', return_value=123456
            ) as mock_get_session_user:
                with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
                    mock_request.headers = {'Authorization': 'Bearer valid_token'}
                    await tester()
        assert mock_validator.called
        assert mock_get_session_user.called
        assert called

    @pytest.mark.asyncio
    async def test__require_session__async__without_header_fails(self):
        called = False

        @require_session
        async def tester(session_user):
            nonlocal called
            called = True
            assert session_user == 123456

        with unittest.mock.patch('bw.auth.decorators.validate_session') as mock_validator:
            with unittest.mock.patch(
                'bw.auth.decorators.SessionStore.get_user_from_session_token', return_value=123456
            ) as mock_get_session_user:
                with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
                    mock_request.headers = {}
                    with pytest.raises(CannotDetermineSession):
                        tester()
        assert not mock_validator.called
        assert not mock_get_session_user.called
        assert not called

    @pytest.mark.asyncio
    async def test__require_session__async__invalid_header_fails(self):
        called = False

        @require_session
        async def tester(session_user):
            nonlocal called
            called = True
            assert session_user == 123456

        with unittest.mock.patch('bw.auth.decorators.validate_session') as mock_validator:
            with unittest.mock.patch(
                'bw.auth.decorators.SessionStore.get_user_from_session_token', return_value=123456
            ) as mock_get_session_user:
                with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
                    mock_request.headers = {'Authorization': 'Meercat valid_token'}
                    with pytest.raises(CannotDetermineSession):
                        await tester()
        assert not mock_validator.called
        assert not mock_get_session_user.called
        assert not called

    @pytest.mark.asyncio
    async def test__require_session__async__validate_session_raises(self):
        called = False

        @require_session
        async def tester(session_user):
            nonlocal called
            called = True
            assert session_user == 123456

        with unittest.mock.patch('bw.auth.decorators.validate_session', side_effect=SessionExpired) as mock_validator:
            with unittest.mock.patch(
                'bw.auth.decorators.SessionStore.get_user_from_session_token', return_value=123456
            ) as mock_get_session_user:
                with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
                    mock_request.headers = {'Authorization': 'Bearer valid_token'}
                    with pytest.raises(SessionExpired):
                        await tester()
        assert mock_validator.called
        assert not mock_get_session_user.called
        assert not called

    @pytest.mark.asyncio
    async def test__require_session__async__get_user_raises(self):
        called = False

        @require_session
        async def tester(session_user):
            nonlocal called
            called = True
            assert session_user == 123456

        with unittest.mock.patch('bw.auth.decorators.validate_session') as mock_validator:
            with unittest.mock.patch(
                'bw.auth.decorators.SessionStore.get_user_from_session_token', side_effect=SessionExpired
            ) as mock_get_session_user:
                with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
                    mock_request.headers = {'Authorization': 'Bearer valid_token'}
                    with pytest.raises(SessionExpired):
                        await tester()
        assert mock_validator.called
        assert mock_get_session_user.called
        assert not called


class TestRequireGroupPermission:
    def test__require_group_permission__sync__succeeds(self, mock_session_user):
        called = False

        @require_group_permission(Permissions.can_test_mission)
        def tester(session_user):
            nonlocal called
            called = True
            assert session_user == mock_session_user

        with unittest.mock.patch('bw.auth.decorators.GroupStore.get_all_permissions_user_has') as mock_getter:
            mock_getter.return_value = Permissions(can_manage_server=False, can_test_mission=True, can_upload_mission=False)
            tester(mock_session_user)
        assert mock_getter.called
        assert called

    def test__require_group_permission__sync__fails_on_invalid_perms(self, mock_session_user):
        called = False

        @require_group_permission(Permissions.can_test_mission)
        def tester(session_user):
            nonlocal called
            called = True

        with unittest.mock.patch('bw.auth.decorators.GroupStore.get_all_permissions_user_has') as mock_getter:
            mock_getter.return_value = Permissions(can_manage_server=True, can_test_mission=False, can_upload_mission=False)
            with pytest.raises(NotEnoughPermissions):
                tester(mock_session_user)
        assert mock_getter.called
        assert not called

    def test__require_group_permission__sync__allows_many_perms_at_once(self, mock_session_user):
        called = False

        @require_group_permission(Permissions.can_test_mission, Permissions.can_upload_mission)
        def tester(session_user):
            nonlocal called
            called = True
            assert session_user == mock_session_user

        with unittest.mock.patch('bw.auth.decorators.GroupStore.get_all_permissions_user_has') as mock_getter:
            mock_getter.return_value = Permissions(can_manage_server=False, can_test_mission=True, can_upload_mission=True)
            tester(mock_session_user)
        assert mock_getter.called
        assert called

        called = False
        with unittest.mock.patch('bw.auth.decorators.GroupStore.get_all_permissions_user_has') as mock_getter:
            mock_getter.return_value = Permissions(can_manage_server=True, can_test_mission=False, can_upload_mission=False)
            with pytest.raises(NotEnoughPermissions):
                tester(mock_session_user)
        assert mock_getter.called
        assert not called

    @pytest.mark.asyncio
    async def test__require_group_permission__async__succeeds(self, mock_session_user):
        called = False

        @require_group_permission(Permissions.can_test_mission)
        async def tester(session_user):
            nonlocal called
            called = True
            assert session_user == mock_session_user

        with unittest.mock.patch('bw.auth.decorators.GroupStore.get_all_permissions_user_has') as mock_getter:
            mock_getter.return_value = Permissions(can_manage_server=False, can_test_mission=True, can_upload_mission=False)
            await tester(mock_session_user)
        assert mock_getter.called
        assert called

    @pytest.mark.asyncio
    async def test__require_group_permission__async__fails_on_invalid_perms(self, mock_session_user):
        called = False

        @require_group_permission(Permissions.can_test_mission)
        async def tester(session_user):
            nonlocal called
            called = True
            assert session_user == mock_session_user

        with unittest.mock.patch('bw.auth.decorators.GroupStore.get_all_permissions_user_has') as mock_getter:
            mock_getter.return_value = Permissions(can_manage_server=True, can_test_mission=False, can_upload_mission=False)
            with pytest.raises(NotEnoughPermissions):
                await tester(mock_session_user)
        assert mock_getter.called
        assert not called

    @pytest.mark.asyncio
    async def test__require_group_permission__async__allows_many_perms_at_once(self, mock_session_user):
        called = False

        @require_group_permission(Permissions.can_test_mission, Permissions.can_upload_mission)
        async def tester(session_user):
            nonlocal called
            called = True
            assert session_user == mock_session_user

        with unittest.mock.patch('bw.auth.decorators.GroupStore.get_all_permissions_user_has') as mock_getter:
            mock_getter.return_value = Permissions(can_manage_server=False, can_test_mission=True, can_upload_mission=True)
            await tester(mock_session_user)
        assert mock_getter.called
        assert called

        called = False
        with unittest.mock.patch('bw.auth.decorators.GroupStore.get_all_permissions_user_has') as mock_getter:
            mock_getter.return_value = Permissions(can_manage_server=True, can_test_mission=False, can_upload_mission=False)
            with pytest.raises(NotEnoughPermissions):
                await tester(mock_session_user)
        assert mock_getter.called
        assert not called


class TestRequireUserRole:
    def test__require_user_role__sync__succeeds(self, mock_session_user):
        called = False

        @require_user_role(Roles.can_create_role)
        def tester(session_user):
            nonlocal called
            called = True
            assert session_user == mock_session_user

        with unittest.mock.patch('bw.auth.decorators.UserStore.get_users_role') as mock_getter:
            mock_getter.return_value = Roles(
                can_create_group=False,
                can_create_role=True,
            )
            tester(mock_session_user)
        assert mock_getter.called
        assert called

    def test__require_user_role__sync__no_role_fails(self, mock_session_user):
        called = False

        @require_user_role(Roles.can_create_role)
        def tester(session_user):
            nonlocal called
            called = True
            assert session_user == mock_session_user

        with unittest.mock.patch('bw.auth.decorators.UserStore.get_users_role') as mock_getter:
            mock_getter.return_value = None
            with pytest.raises(NotEnoughPermissions):
                tester(mock_session_user)
        assert mock_getter.called
        assert not called

    def test__require_user_role__sync__fails_on_invalid_perms(self, mock_session_user):
        called = False

        @require_user_role(Roles.can_create_role)
        def tester(session_user):
            nonlocal called
            called = True

        with unittest.mock.patch('bw.auth.decorators.UserStore.get_users_role') as mock_getter:
            mock_getter.return_value = Roles(
                can_create_group=False,
                can_create_role=False,
            )
            with pytest.raises(NotEnoughPermissions):
                tester(mock_session_user)
        assert mock_getter.called
        assert not called

    def test__require_user_role__sync__allows_many_perms_at_once(self, mock_session_user):
        called = False

        @require_user_role(Roles.can_create_role, Roles.can_create_group)
        def tester(session_user):
            nonlocal called
            called = True
            assert session_user == mock_session_user

        with unittest.mock.patch('bw.auth.decorators.UserStore.get_users_role') as mock_getter:
            mock_getter.return_value = Roles(
                can_create_group=True,
                can_create_role=True,
            )
            tester(mock_session_user)
        assert mock_getter.called
        assert called

        called = False
        with unittest.mock.patch('bw.auth.decorators.UserStore.get_users_role') as mock_getter:
            mock_getter.return_value = Roles(
                can_create_group=True,
                can_create_role=False,
            )
            with pytest.raises(NotEnoughPermissions):
                tester(mock_session_user)
        assert mock_getter.called
        assert not called

    @pytest.mark.asyncio
    async def test__require_user_role__async__succeeds(self, mock_session_user):
        called = False

        @require_user_role(Roles.can_create_group)
        async def tester(session_user):
            nonlocal called
            called = True
            assert session_user == mock_session_user

        with unittest.mock.patch('bw.auth.decorators.UserStore.get_users_role') as mock_getter:
            mock_getter.return_value = Roles(can_create_group=True, can_create_role=False)
            await tester(mock_session_user)
        assert mock_getter.called
        assert called

    @pytest.mark.asyncio
    async def test__require_user_role__async__no_role_fails(self, mock_session_user):
        called = False

        @require_user_role(Roles.can_create_role)
        async def tester(session_user):
            nonlocal called
            called = True
            assert session_user == mock_session_user

        with unittest.mock.patch('bw.auth.decorators.UserStore.get_users_role') as mock_getter:
            mock_getter.return_value = None
            with pytest.raises(NotEnoughPermissions):
                await tester(mock_session_user)
        assert mock_getter.called
        assert not called

    @pytest.mark.asyncio
    async def test__require_user_role__async__fails_on_invalid_perms(self, mock_session_user):
        called = False

        @require_user_role(Roles.can_create_group)
        async def tester(session_user):
            nonlocal called
            called = True
            assert session_user == mock_session_user

        with unittest.mock.patch('bw.auth.decorators.UserStore.get_users_role') as mock_getter:
            mock_getter.return_value = Roles(can_create_group=False, can_create_role=False)
            with pytest.raises(NotEnoughPermissions):
                await tester(mock_session_user)
        assert mock_getter.called
        assert not called

    @pytest.mark.asyncio
    async def test__require_user_role__async__allows_many_perms_at_once(self, mock_session_user):
        called = False

        @require_user_role(Roles.can_create_group, Roles.can_create_role)
        async def tester(session_user):
            nonlocal called
            called = True
            assert session_user == mock_session_user

        with unittest.mock.patch('bw.auth.decorators.UserStore.get_users_role') as mock_getter:
            mock_getter.return_value = Roles(can_create_group=True, can_create_role=True)
            await tester(mock_session_user)
        assert mock_getter.called
        assert called

        called = False
        with unittest.mock.patch('bw.auth.decorators.UserStore.get_users_role') as mock_getter:
            mock_getter.return_value = Roles(can_create_group=False, can_create_role=False)
            with pytest.raises(NotEnoughPermissions):
                await tester(mock_session_user)
        assert mock_getter.called
        assert not called
