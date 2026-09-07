# ruff: noqa: F811, F401

import re
import unittest
import unittest.mock

import pytest

from bw.auth.group import GroupStore
from bw.auth.roles import Roles
from bw.auth.session import SessionStore
from bw.auth.user import UserStore
from integrations.auth.fixtures import (
    db_bot_user_1,
    db_bourbon_code_1,
    db_bourbon_user_1,
    db_discord_user_1,
    db_expired_session_1,
    db_group_1,
    db_group_2,
    db_group_assigner,
    db_permission_1,
    db_permission_2,
    db_role_1,
    db_role_2,
    db_role_assigner,
    db_session_1,
    db_unverified_bourbon_user,
    db_user_1,
    db_user_2,
    discord_id_1,
    discord_token_1,
    discord_token_2,
    email_1,
    email_2,
    endpoint_api_local_url,
    endpoint_api_url,
    endpoint_api_v1_url,
    endpoint_local_user_create_bot_url,
    endpoint_local_user_role_assign_url,
    endpoint_local_user_role_create_url,
    endpoint_login_bot_url,
    endpoint_user_group_create_permission_url,
    endpoint_user_group_create_url,
    endpoint_user_group_join_url,
    endpoint_user_group_leave_url,
    endpoint_user_recover_reset_url,
    endpoint_user_recover_url,
    endpoint_user_role_assign_url,
    endpoint_user_role_create_url,
    endpoint_user_url,
    endpoint_user_verify_resend_url,
    expire_invalid,
    expire_valid,
    frontend_recover_url,
    frontend_verify_url,
    group_assigner,
    group_name_1,
    group_name_2,
    invalid_discord_token,
    make_mock_discord_response,
    new_discord_id,
    oauth_code_1,
    oauth_state_1,
    oauth_state_2,
    password_1,
    password_2,
    permission_1,
    permission_2,
    permission_name_1,
    permission_name_2,
    role_1,
    role_assigner,
    role_name_1,
    role_name_2,
    salt_1,
    salt_2,
    token_1,
    token_2,
    username_1,
    username_2,
)
from integrations.fixtures import test_app


def csrf_token_from_html(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match is not None
    return match.group(1)


class TestLoginBotEndpoints:
    @pytest.mark.asyncio
    async def test__login_bot__session_created_with_bot(self, state, test_app, endpoint_login_bot_url, db_bot_user_1):
        response = await test_app.post(endpoint_login_bot_url, json={'bot_token': db_bot_user_1.bot_token})
        assert response.status_code == 200
        data = await response.get_json()
        assert 'session_token' in data
        assert SessionStore().is_session_active(state, data['session_token'])

    @pytest.mark.asyncio
    async def test__login_bot__session_not_created_no_bot(self, state, test_app, endpoint_login_bot_url):
        response = await test_app.post(endpoint_login_bot_url, json={'bot_token': 'fooet'})
        assert response.status_code == 404
        assert not SessionStore().is_session_active(state, 'fooet')


class TestUserEndpoints:
    @pytest.mark.asyncio
    async def test__user__gets_user_data(
        self, state, test_app, endpoint_user_url, token_1, db_user_1, db_session_1, db_group_1, db_group_2
    ):
        GroupStore().assign_user_to_group(state, db_user_1, db_group_1)
        GroupStore().assign_user_to_group(state, db_user_1, db_group_2)

        response = await test_app.get(endpoint_user_url, headers={'Authorization': f'Bearer {token_1}'})
        assert response.status_code == 200
        data = await response.get_json()
        assert data['uuid'] == str(db_user_1.uuid)
        assert data['creation_date'] == db_user_1.creation_date.isoformat()
        assert data['groups'] == [db_group_1.name, db_group_2.name]

    @pytest.mark.asyncio
    async def test__user__no_token_gets_no_data(self, state, test_app, endpoint_user_url):
        response = await test_app.get(endpoint_user_url)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test__user__expired_session_no_data(self, state, test_app, endpoint_user_url, db_expired_session_1):
        response = await test_app.get(endpoint_user_url, headers={'Authorization': f'Bearer {db_expired_session_1.token}'})
        assert response.status_code == 401


class TestRecoveryEndpoints:
    @pytest.mark.asyncio
    async def test__recover_page__renders_recovery_form(self, test_app, frontend_recover_url):
        """Test that GET /recover renders the recovery email form."""
        # Not yet reviewed
        response = await test_app.get(frontend_recover_url)
        html = await response.get_data(as_text=True)

        assert response.status_code == 200
        assert 'Recover Account' in html
        assert '/api/v1/user/recover' in html

    @pytest.mark.asyncio
    async def test__recover_page__renders_reset_form_with_token(self, test_app, frontend_recover_url, token_1):
        """Test that GET /recover with a token renders the password reset form."""
        # Not yet reviewed
        response = await test_app.get(f'{frontend_recover_url}?token={token_1}')
        html = await response.get_data(as_text=True)

        assert response.status_code == 200
        assert 'Reset password' in html
        assert token_1 in html
        assert '/api/v1/user/recover/reset' in html

    @pytest.mark.asyncio
    async def test__recover__accepts_recovery_request(
        self, mocker, state, test_app, db_bourbon_user_1, endpoint_user_recover_url, frontend_recover_url, email_1
    ):
        """Test that POST /user/recover accepts a recovery request."""
        # Not yet reviewed
        mocker.patch('bw.auth.api.ENVIRONMENT.verify_immediately', return_value=True)
        page = await test_app.get(frontend_recover_url)
        csrf_token = csrf_token_from_html(await page.get_data(as_text=True))

        response = await test_app.post(endpoint_user_recover_url, form={'csrf_token': csrf_token, 'email': email_1})
        html = await response.get_data(as_text=True)

        assert response.status_code == 200
        assert 'Check your email' in html

    @pytest.mark.asyncio
    async def test__recover__rejects_invalid_csrf(self, test_app, endpoint_user_recover_url, email_1):
        """Test that POST /user/recover rejects an invalid CSRF token."""
        # Not yet reviewed
        response = await test_app.post(endpoint_user_recover_url, form={'csrf_token': 'invalid', 'email': email_1})

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test__recover_reset__changes_password(
        self,
        state,
        test_app,
        db_user_1,
        db_bourbon_user_1,
        db_bourbon_code_1,
        endpoint_user_recover_reset_url,
        frontend_recover_url,
        password_2,
    ):
        """Test that POST /user/recover/reset changes the user's password."""
        # Not yet reviewed
        page = await test_app.get(f'{frontend_recover_url}?token={db_bourbon_code_1.code}')
        csrf_token = csrf_token_from_html(await page.get_data(as_text=True))

        response = await test_app.post(
            endpoint_user_recover_reset_url,
            form={'csrf_token': csrf_token, 'token': db_bourbon_code_1.code, 'password': password_2},
        )
        html = await response.get_data(as_text=True)
        bourbon_user = UserStore().bourbon_user_from_user(state, db_user_1)

        assert response.status_code == 200
        assert 'Password reset' in html
        bourbon_user.verify_password(password_2)

    @pytest.mark.asyncio
    async def test__recover_reset__rejects_invalid_token(
        self, test_app, endpoint_user_recover_reset_url, frontend_recover_url, token_1, password_2
    ):
        """Test that POST /user/recover/reset rejects an invalid recovery token."""
        # Not yet reviewed
        page = await test_app.get(f'{frontend_recover_url}?token={token_1}')
        csrf_token = csrf_token_from_html(await page.get_data(as_text=True))

        response = await test_app.post(
            endpoint_user_recover_reset_url,
            form={'csrf_token': csrf_token, 'token': token_1, 'password': password_2},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test__verify_resend__accepts_unverified_account(
        self, mocker, test_app, db_unverified_bourbon_user, endpoint_user_verify_resend_url, frontend_recover_url, email_2
    ):
        """Test that POST /user/verify/resend accepts an unverified account."""
        # Not yet reviewed
        mocker.patch('bw.auth.api.ENVIRONMENT.verify_immediately', return_value=True)
        page = await test_app.get(frontend_recover_url)
        csrf_token = csrf_token_from_html(await page.get_data(as_text=True))

        response = await test_app.post(endpoint_user_verify_resend_url, form={'csrf_token': csrf_token, 'email': email_2})
        html = await response.get_data(as_text=True)

        assert response.status_code == 200
        assert 'Check your email' in html

    @pytest.mark.asyncio
    async def test__verify_page__invalid_token_renders_error(self, test_app, frontend_verify_url, token_1):
        """Test that GET /verify renders the error state for an invalid token."""
        # Not yet reviewed
        response = await test_app.get(f'{frontend_verify_url}?token={token_1}')
        html = await response.get_data(as_text=True)

        assert response.status_code == 200
        assert 'An error has occured' in html


class TestRoleEndpoints:
    @pytest.mark.asyncio
    async def test__create_role__role_created(
        self, state, test_app, db_user_1, role_1, db_session_1, db_role_assigner, endpoint_user_role_create_url
    ):
        UserStore().assign_user_role(state, db_user_1, db_role_assigner.name)

        response = await test_app.post(
            endpoint_user_role_create_url,
            json={'role_name': 'test_role', **role_1.as_dict()},
            headers={'Authorization': f'Bearer {db_session_1.token}'},
        )
        assert response.status_code == 201
        data = await response.get_json()
        assert data['name'] == 'test_role'

    @pytest.mark.asyncio
    async def test__create_role__cant_create_if_not_permitted(
        self, state, test_app, db_user_1, role_1, db_session_1, endpoint_user_role_create_url
    ):
        response = await test_app.post(
            endpoint_user_role_create_url,
            json={'role_name': 'test_role', **role_1.as_dict()},
            headers={'Authorization': f'Bearer {db_session_1.token}'},
        )
        assert response.status_code == 403
        assert len(UserStore().get_all_roles(state)) == 0

    @pytest.mark.asyncio
    async def test__create_role__expired_session_nothing(
        self, state, test_app, db_user_1, role_1, db_expired_session_1, db_role_assigner, endpoint_user_role_create_url
    ):
        UserStore().assign_user_role(state, db_user_1, db_role_assigner.name)
        assert len(UserStore().get_all_roles(state)) == 1

        response = await test_app.post(
            endpoint_user_role_create_url,
            json={'role_name': 'test_role', **role_1.as_dict()},
            headers={'Authorization': f'Bearer {db_expired_session_1.token}'},
        )
        assert response.status_code == 401
        assert len(UserStore().get_all_roles(state)) == 1

    @pytest.mark.asyncio
    async def test__create_role__cant_create_duplicate(
        self, state, test_app, db_user_1, role_1, db_role_1, db_session_1, db_role_assigner, endpoint_user_role_create_url
    ):
        UserStore().assign_user_role(state, db_user_1, db_role_assigner.name)

        response = await test_app.post(
            endpoint_user_role_create_url,
            json={'role_name': db_role_1.name, **role_1.as_dict()},
            headers={'Authorization': f'Bearer {db_session_1.token}'},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test__assign_role__can_assign_role(
        self, state, test_app, db_user_1, db_user_2, db_role_1, db_session_1, db_role_assigner, endpoint_user_role_assign_url
    ):
        UserStore().assign_user_role(state, db_user_1, db_role_assigner.name)

        response = await test_app.post(
            endpoint_user_role_assign_url,
            json={'user_uuid': str(db_user_2.uuid), 'role_name': db_role_1.name},
            headers={'Authorization': f'Bearer {db_session_1.token}'},
        )
        assert response.status_code == 200
        assert UserStore().get_users_role(state, db_user_1).as_dict() == db_role_1.into_roles().as_dict()

    @pytest.mark.asyncio
    async def test__assign_role__cant_assign_if_not_permitted(
        self, state, test_app, db_user_1, db_user_2, role_1, db_session_1, endpoint_user_role_assign_url
    ):
        response = await test_app.post(
            endpoint_user_role_assign_url,
            json={'user_uuid': str(db_user_2.uuid), 'role_name': db_role_1.name},
            headers={'Authorization': f'Bearer {db_session_1.token}'},
        )
        assert response.status_code == 403
        assert UserStore().get_users_role(state, db_user_1) is None

    @pytest.mark.asyncio
    async def test__assign_role__cant_assign_if_expired_session(
        self,
        state,
        test_app,
        db_user_1,
        db_user_2,
        db_role_1,
        db_expired_session_1,
        db_role_assigner,
        endpoint_user_role_assign_url,
    ):
        UserStore().assign_user_role(state, db_user_1, db_role_assigner.name)

        response = await test_app.post(
            endpoint_user_role_assign_url,
            json={'user_uuid': str(db_user_2.uuid), 'role_name': db_role_1.name},
            headers={'Authorization': f'Bearer {db_expired_session_1.token}'},
        )
        assert response.status_code == 401
        assert UserStore().get_users_role(state, db_user_2) is None

    @pytest.mark.asyncio
    async def test__assign_role__cant_assign_nonexistent(
        self, state, test_app, db_user_1, db_user_2, db_session_1, db_role_assigner, endpoint_user_role_assign_url
    ):
        UserStore().assign_user_role(state, db_user_1, db_role_assigner.name)

        response = await test_app.post(
            endpoint_user_role_assign_url,
            json={'user_uuid': str(db_user_2.uuid), 'role_name': 'fooeybarjkdsr'},
            headers={'Authorization': f'Bearer {db_session_1.token}'},
        )
        assert response.status_code == 404
        assert UserStore().get_users_role(state, db_user_2) is None


class TestLocalAuthEndpoints:
    @pytest.mark.asyncio
    async def test__local_create_bot__can_create(self, state, test_app, endpoint_local_user_create_bot_url):
        with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
            mock_request.remote_addr = '127.0.0.1'
            response = await test_app.post(endpoint_local_user_create_bot_url)
        assert response.status_code == 201
        json = await response.get_json()
        assert UserStore().user_from_bot_token(state, json['bot_token']) is not None

    @pytest.mark.asyncio
    async def test__local_create_bot__cant_create_remote(self, state, test_app, endpoint_local_user_create_bot_url):
        with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
            mock_request.remote_addr = '8.8.8.8'
            response = await test_app.post(endpoint_local_user_create_bot_url)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test__local_create_role__role_created(
        self, state, test_app, db_user_1, role_1, db_session_1, db_role_assigner, endpoint_local_user_role_create_url
    ):
        UserStore().assign_user_role(state, db_user_1, db_role_assigner.name)

        with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
            mock_request.remote_addr = '127.0.0.1'
            mock_request.headers = {'Authorization': f'Bearer {db_session_1.token}'}
            response = await test_app.post(
                endpoint_local_user_role_create_url,
                json={'role_name': 'test_role', **role_1.as_dict()},
                headers={'Authorization': f'Bearer {db_session_1.token}'},
            )
        assert response.status_code == 201
        data = await response.get_json()
        assert data['name'] == 'test_role'

    @pytest.mark.asyncio
    async def test__local_create_role__expired_session_nothing(
        self, state, test_app, db_user_1, role_1, db_expired_session_1, db_role_assigner, endpoint_local_user_role_create_url
    ):
        UserStore().assign_user_role(state, db_user_1, db_role_assigner.name)
        assert len(UserStore().get_all_roles(state)) == 1

        with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
            mock_request.remote_addr = '127.0.0.1'
            mock_request.headers = {'Authorization': f'Bearer {db_expired_session_1.token}'}
            response = await test_app.post(
                endpoint_local_user_role_create_url,
                json={'role_name': 'test_role', **role_1.as_dict()},
                headers={'Authorization': f'Bearer {db_expired_session_1.token}'},
            )
        assert response.status_code == 401
        assert len(UserStore().get_all_roles(state)) == 1

    @pytest.mark.asyncio
    async def test__local_create_role__cant_create_duplicate(
        self, state, test_app, db_user_1, role_1, db_role_1, db_session_1, db_role_assigner, endpoint_local_user_role_create_url
    ):
        UserStore().assign_user_role(state, db_user_1, db_role_assigner.name)

        with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
            mock_request.remote_addr = '127.0.0.1'
            mock_request.headers = {'Authorization': f'Bearer {db_session_1.token}'}
            response = await test_app.post(
                endpoint_local_user_role_create_url,
                json={'role_name': db_role_1.name, **role_1.as_dict()},
                headers={'Authorization': f'Bearer {db_session_1.token}'},
            )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test__local_assign_role__can_local_assign_role(
        self,
        state,
        test_app,
        db_user_1,
        db_user_2,
        db_role_1,
        db_session_1,
        db_role_assigner,
        endpoint_local_user_role_assign_url,
    ):
        UserStore().assign_user_role(state, db_user_1, db_role_assigner.name)

        with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
            mock_request.remote_addr = '127.0.0.1'
            mock_request.headers = {'Authorization': f'Bearer {db_session_1.token}'}
            response = await test_app.post(
                endpoint_local_user_role_assign_url,
                json={'user_uuid': str(db_user_2.uuid), 'role_name': db_role_1.name},
                headers={'Authorization': f'Bearer {db_session_1.token}'},
            )
        assert response.status_code == 200
        assert UserStore().get_users_role(state, db_user_1).as_dict() == db_role_1.into_roles().as_dict()

    @pytest.mark.asyncio
    async def test__local_assign_role__cant_assign_if_expired_session(
        self,
        state,
        test_app,
        db_user_1,
        db_user_2,
        db_role_1,
        db_expired_session_1,
        db_role_assigner,
        endpoint_local_user_role_assign_url,
    ):
        UserStore().assign_user_role(state, db_user_1, db_role_assigner.name)

        with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
            mock_request.remote_addr = '127.0.0.1'
            mock_request.headers = {'Authorization': f'Bearer {db_expired_session_1.token}'}
            response = await test_app.post(
                endpoint_local_user_role_assign_url,
                json={'user_uuid': str(db_user_2.uuid), 'role_name': db_role_1.name},
                headers={'Authorization': f'Bearer {db_expired_session_1.token}'},
            )
        assert response.status_code == 401
        assert UserStore().get_users_role(state, db_user_2) is None

    @pytest.mark.asyncio
    async def test__local_assign_role__cant_assign_nonexistent(
        self, state, test_app, db_user_1, db_user_2, db_session_1, db_role_assigner, endpoint_local_user_role_assign_url
    ):
        UserStore().assign_user_role(state, db_user_1, db_role_assigner.name)

        with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
            mock_request.remote_addr = '127.0.0.1'
            mock_request.headers = {'Authorization': f'Bearer {db_session_1.token}'}
            response = await test_app.post(
                endpoint_local_user_role_assign_url,
                json={'user_uuid': str(db_user_2.uuid), 'role_name': 'fooeybarjkdsr'},
                headers={'Authorization': f'Bearer {db_session_1.token}'},
            )
        assert response.status_code == 404
        assert UserStore().get_users_role(state, db_user_2) is None

    @pytest.mark.asyncio
    async def test__local_create_role__cant_create_remote(
        self, state, test_app, db_user_1, role_1, db_session_1, db_role_assigner, endpoint_local_user_role_create_url
    ):
        UserStore().assign_user_role(state, db_user_1, db_role_assigner.name)

        with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
            mock_request.remote_addr = '8.8.8.8'
            mock_request.headers = {'Authorization': f'Bearer {db_session_1.token}'}
            response = await test_app.post(
                endpoint_local_user_role_create_url,
                json={'role_name': 'test_role', **role_1.as_dict()},
                headers={'Authorization': f'Bearer {db_session_1.token}'},
            )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test__local_assign_role__cant_assign_remote(
        self,
        state,
        test_app,
        db_user_1,
        db_user_2,
        db_role_1,
        db_session_1,
        db_role_assigner,
        endpoint_local_user_role_assign_url,
    ):
        UserStore().assign_user_role(state, db_user_1, db_role_assigner.name)

        with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
            mock_request.remote_addr = '8.8.8.8'
            mock_request.headers = {'Authorization': f'Bearer {db_session_1.token}'}
            response = await test_app.post(
                endpoint_local_user_role_assign_url,
                json={'user_uuid': str(db_user_2.uuid), 'role_name': db_role_1.name},
                headers={'Authorization': f'Bearer {db_session_1.token}'},
            )
        assert response.status_code == 403


class TestGroupEndpoints:
    @pytest.mark.asyncio
    async def test__create_group_permission__permission_created(
        self, state, test_app, db_user_1, permission_1, db_session_1, db_group_assigner, endpoint_user_group_create_permission_url
    ):
        UserStore().assign_user_role(state, db_user_1, db_group_assigner.name)

        response = await test_app.post(
            endpoint_user_group_create_permission_url,
            json={'permission_name': 'test_permission', **permission_1.as_dict()},
            headers={'Authorization': f'Bearer {db_session_1.token}'},
        )
        assert response.status_code == 201
        data = await response.get_json()
        assert data['name'] == 'test_permission'

    @pytest.mark.asyncio
    async def test__create_group_permission__cant_create_if_not_permitted(
        self, state, test_app, db_user_1, permission_1, db_session_1, endpoint_user_group_create_permission_url
    ):
        response = await test_app.post(
            endpoint_user_group_create_permission_url,
            json={'permission_name': 'test_permission', **permission_1.as_dict()},
            headers={'Authorization': f'Bearer {db_session_1.token}'},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test__create_group_permission__expired_session_nothing(
        self,
        state,
        test_app,
        db_user_1,
        permission_1,
        db_expired_session_1,
        db_group_assigner,
        endpoint_user_group_create_permission_url,
    ):
        UserStore().assign_user_role(state, db_user_1, db_group_assigner.name)

        response = await test_app.post(
            endpoint_user_group_create_permission_url,
            json={'permission_name': 'test_permission', **permission_1.as_dict()},
            headers={'Authorization': f'Bearer {db_expired_session_1.token}'},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test__create_group__group_created(
        self, state, test_app, db_user_1, db_permission_1, db_session_1, db_group_assigner, endpoint_user_group_create_url
    ):
        UserStore().assign_user_role(state, db_user_1, db_group_assigner.name)

        response = await test_app.post(
            endpoint_user_group_create_url,
            json={'group_name': 'test_group', 'permissions': db_permission_1.name},
            headers={'Authorization': f'Bearer {db_session_1.token}'},
        )
        assert response.status_code == 201
        data = await response.get_json()
        assert data['name'] == 'test_group'

    @pytest.mark.asyncio
    async def test__create_group__cant_create_if_not_permitted(
        self, state, test_app, db_user_1, db_permission_1, db_session_1, endpoint_user_group_create_url
    ):
        response = await test_app.post(
            endpoint_user_group_create_url,
            json={'group_name': 'test_group', 'permissions': db_permission_1.name},
            headers={'Authorization': f'Bearer {db_session_1.token}'},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test__create_group__expired_session_nothing(
        self, state, test_app, db_user_1, db_permission_1, db_expired_session_1, db_group_assigner, endpoint_user_group_create_url
    ):
        UserStore().assign_user_role(state, db_user_1, db_group_assigner.name)

        response = await test_app.post(
            endpoint_user_group_create_url,
            json={'group_name': 'test_group', 'permissions': db_permission_1.name},
            headers={'Authorization': f'Bearer {db_expired_session_1.token}'},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test__join_group__can_join_group(
        self, state, test_app, db_user_1, db_group_1, db_session_1, endpoint_user_group_join_url
    ):
        response = await test_app.post(
            endpoint_user_group_join_url,
            json={'group_name': db_group_1.name},
            headers={'Authorization': f'Bearer {db_session_1.token}'},
        )
        assert response.status_code == 200

        user_groups = GroupStore().get_user_groups(state, db_user_1)
        assert any(group.name == db_group_1.name for group in user_groups)

    @pytest.mark.asyncio
    async def test__join_group__cant_join_nonexistent_group(
        self, state, test_app, db_user_1, db_session_1, endpoint_user_group_join_url
    ):
        response = await test_app.post(
            endpoint_user_group_join_url,
            json={'group_name': 'nonexistent_group'},
            headers={'Authorization': f'Bearer {db_session_1.token}'},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test__join_group__expired_session_nothing(
        self, state, test_app, db_user_1, db_group_1, db_expired_session_1, endpoint_user_group_join_url
    ):
        response = await test_app.post(
            endpoint_user_group_join_url,
            json={'group_name': db_group_1.name},
            headers={'Authorization': f'Bearer {db_expired_session_1.token}'},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test__leave_group__can_leave_group(
        self, state, test_app, db_user_1, db_group_1, db_session_1, endpoint_user_group_leave_url
    ):
        response = await test_app.post(
            endpoint_user_group_leave_url,
            json={'group_name': db_group_1.name},
            headers={'Authorization': f'Bearer {db_session_1.token}'},
        )
        assert response.status_code == 200

        user_groups = GroupStore().get_user_groups(state, db_user_1)
        assert not any(group.name == db_group_1.name for group in user_groups)

    @pytest.mark.asyncio
    async def test__leave_group__cant_leave_nonexistent_group(
        self, state, test_app, db_user_1, db_session_1, endpoint_user_group_leave_url
    ):
        response = await test_app.post(
            endpoint_user_group_leave_url,
            json={'group_name': 'nonexistent_group'},
            headers={'Authorization': f'Bearer {db_session_1.token}'},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test__leave_group__expired_session_nothing(
        self, state, test_app, db_user_1, db_group_1, db_expired_session_1, endpoint_user_group_leave_url
    ):
        response = await test_app.post(
            endpoint_user_group_leave_url,
            json={'group_name': db_group_1.name},
            headers={'Authorization': f'Bearer {db_expired_session_1.token}'},
        )
        assert response.status_code == 401


class TestDiscordEndpoints:
    @pytest.mark.asyncio
    async def test__login_discord_redirect__returns_html(self, state, test_app, oauth_code_1, oauth_state_1):
        response = await test_app.get(f'/auth/login/discord?code={oauth_code_1}&state={oauth_state_1}')
        assert response.status_code == 200
        assert response.content_type.startswith('text/html')

    @pytest.mark.asyncio
    async def test__login_discord_redirect__handles_missing_code(self, state, test_app, oauth_state_2):
        response = await test_app.get(f'/auth/login/discord?state={oauth_state_2}')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test__login_discord__creates_session_for_existing_user(
        self,
        mocker,
        state,
        test_app,
        db_discord_user_1,
        discord_id_1,
        token_1,
        expire_valid,
        discord_token_1,
        make_mock_discord_response,
    ):
        mock_response = make_mock_discord_response(discord_id_1)

        mocker.patch('secrets.token_urlsafe', return_value=token_1)
        mocker.patch('bw.models.auth.Session.human_session_length', return_value=expire_valid)
        mocker.patch('bw.auth.api.ENVIRONMENT.discord_api_url', return_value='https://discord.com/api')
        mocker.patch('bw.auth.api.aiohttp.ClientSession.get', return_value=mock_response)

        response = await test_app.post('/api/v1/auth/login/discord', headers={'Authorization': f'Bearer {discord_token_1}'})

        assert response.status_code == 200
        data = await response.get_json()
        assert 'session_token' in data
        assert 'expire_time' in data

    @pytest.mark.asyncio
    async def test__login_discord__creates_new_user_for_new_discord_id(
        self, mocker, state, test_app, token_1, expire_valid, discord_token_2, new_discord_id, make_mock_discord_response
    ):
        mock_response = make_mock_discord_response(new_discord_id)

        mocker.patch('secrets.token_urlsafe', return_value=token_1)
        mocker.patch('bw.models.auth.Session.human_session_length', return_value=expire_valid)
        mocker.patch('bw.auth.api.ENVIRONMENT.discord_api_url', return_value='https://discord.com/api')
        mocker.patch('bw.auth.api.aiohttp.ClientSession.get', return_value=mock_response)

        response = await test_app.post('/api/v1/auth/login/discord', headers={'Authorization': f'Bearer {discord_token_2}'})

        assert response.status_code == 200
        data = await response.get_json()
        assert 'session_token' in data
        assert 'expire_time' in data

    @pytest.mark.asyncio
    async def test__login_discord__returns_401_for_invalid_token(
        self, mocker, state, test_app, discord_id_1, invalid_discord_token, make_mock_discord_response
    ):
        mock_response = make_mock_discord_response(discord_id=discord_id_1, should_raise=True, error_status=401)

        mocker.patch('bw.auth.api.ENVIRONMENT.discord_api_url', return_value='https://discord.com/api')
        mocker.patch('bw.auth.api.aiohttp.ClientSession.get', return_value=mock_response)

        response = await test_app.post('/api/v1/auth/login/discord', headers={'Authorization': f'Bearer {invalid_discord_token}'})

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test__login_discord__requires_authorization_header(self, state, test_app):
        response = await test_app.post('/api/v1/auth/login/discord')
        assert response.status_code == 401
