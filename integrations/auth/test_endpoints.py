# ruff: noqa: F811, F401

import pytest
import unittest
import unittest.mock

from integrations.fixtures import test_app, session, state
from integrations.auth.fixtures import (
    endpoint_api_url,
    endpoint_api_v1_url,
    endpoint_api_local_url,
    endpoint_login_bot_url,
    endpoint_user_url,
    endpoint_user_role_create_url,
    endpoint_user_role_assign_url,
    endpoint_user_group_create_permission_url,
    endpoint_user_group_create_url,
    endpoint_user_group_join_url,
    endpoint_user_group_leave_url,
    endpoint_local_user_create_bot_url,
    endpoint_local_user_role_create_url,
    endpoint_local_user_role_assign_url,
    token_1,
    db_user_1,
    token_2,
    db_user_2,
    db_bot_user_1,
    db_session_1,
    group_name_1,
    permission_name_1,
    permission_1,
    db_permission_1,
    db_group_1,
    group_name_2,
    permission_name_2,
    permission_2,
    db_permission_2,
    db_group_2,
    role_1,
    role_assigner,
    group_assigner,
    expire_invalid,
    db_expired_session_1,
    role_name_1,
    role_name_2,
    db_role_1,
    db_role_2,
    db_role_assigner,
    db_group_assigner,
    invalid_discord_token,
    expire_valid,
    discord_id_1,
    db_discord_user_1,
    discord_token_1,
    discord_token_2,
    oauth_state_1,
    oauth_state_2,
    oauth_code_1,
    make_mock_discord_response,
    new_discord_id,
)
from bw.auth.user import UserStore
from bw.auth.group import GroupStore
from bw.auth.session import SessionStore
from bw.auth.roles import Roles


@pytest.mark.asyncio
async def test__login_bot__session_created_with_bot(state, session, test_app, endpoint_login_bot_url, db_bot_user_1):
    response = await test_app.post(endpoint_login_bot_url, json={'bot_token': db_bot_user_1.bot_token})
    assert response.status_code == 200
    data = await response.get_json()
    assert 'session_token' in data

    assert SessionStore().is_session_active(state, data['session_token'])


@pytest.mark.asyncio
async def test__login_bot__session_not_created_no_bot(state, session, test_app, endpoint_login_bot_url):
    response = await test_app.post(endpoint_login_bot_url, json={'bot_token': 'fooet'})
    assert response.status_code == 404
    assert not SessionStore().is_session_active(state, 'fooet')


@pytest.mark.asyncio
async def test__user__gets_user_data(
    state, session, test_app, endpoint_user_url, token_1, db_user_1, db_session_1, db_group_1, db_group_2
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
async def test__user__no_token_gets_no_data(state, session, test_app, endpoint_user_url):
    response = await test_app.get(endpoint_user_url)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test__user__expired_session_no_data(state, session, test_app, endpoint_user_url, db_expired_session_1):
    response = await test_app.get(endpoint_user_url, headers={'Authorization': f'Bearer {db_expired_session_1.token}'})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test__create_role__role_created(
    state, session, test_app, db_user_1, role_1, db_session_1, db_role_assigner, endpoint_user_role_create_url
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
    state, session, test_app, db_user_1, role_1, db_session_1, endpoint_user_role_create_url
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
    state, session, test_app, db_user_1, role_1, db_expired_session_1, db_role_assigner, endpoint_user_role_create_url
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
    state, session, test_app, db_user_1, role_1, db_role_1, db_session_1, db_role_assigner, endpoint_user_role_create_url
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
    state, session, test_app, db_user_1, db_user_2, db_role_1, db_session_1, db_role_assigner, endpoint_user_role_assign_url
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
    state, session, test_app, db_user_1, db_user_2, role_1, db_session_1, endpoint_user_role_assign_url
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
    state,
    session,
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
    state, session, test_app, db_user_1, db_user_2, db_session_1, db_role_assigner, endpoint_user_role_assign_url
):
    UserStore().assign_user_role(state, db_user_1, db_role_assigner.name)

    response = await test_app.post(
        endpoint_user_role_assign_url,
        json={'user_uuid': str(db_user_2.uuid), 'role_name': 'fooeybarjkdsr'},
        headers={'Authorization': f'Bearer {db_session_1.token}'},
    )
    assert response.status_code == 404
    assert UserStore().get_users_role(state, db_user_2) is None


@pytest.mark.asyncio
async def test__local_create_bot__can_create(state, session, test_app, endpoint_local_user_create_bot_url):
    with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
        mock_request.remote_addr = '127.0.0.1'
        response = await test_app.post(endpoint_local_user_create_bot_url)
    assert response.status_code == 201
    json = await response.get_json()
    assert UserStore().user_from_bot_token(state, json['bot_token']) is not None


@pytest.mark.asyncio
async def test__local_create_bot__cant_create_remote(state, session, test_app, endpoint_local_user_create_bot_url):
    with unittest.mock.patch('bw.auth.decorators.request', new_callable=unittest.mock.PropertyMock) as mock_request:
        mock_request.remote_addr = '8.8.8.8'
        response = await test_app.post(endpoint_local_user_create_bot_url)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__local_create_role__role_created(
    state, session, test_app, db_user_1, role_1, db_session_1, db_role_assigner, endpoint_local_user_role_create_url
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
    state, session, test_app, db_user_1, role_1, db_expired_session_1, db_role_assigner, endpoint_local_user_role_create_url
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
    state, session, test_app, db_user_1, role_1, db_role_1, db_session_1, db_role_assigner, endpoint_local_user_role_create_url
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
    state, session, test_app, db_user_1, db_user_2, db_role_1, db_session_1, db_role_assigner, endpoint_local_user_role_assign_url
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
    state,
    session,
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
    state, session, test_app, db_user_1, db_user_2, db_session_1, db_role_assigner, endpoint_local_user_role_assign_url
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
    state, session, test_app, db_user_1, role_1, db_session_1, db_role_assigner, endpoint_local_user_role_create_url
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
    state, session, test_app, db_user_1, db_user_2, db_role_1, db_session_1, db_role_assigner, endpoint_local_user_role_assign_url
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


# Group endpoint tests
@pytest.mark.asyncio
async def test__create_group_permission__permission_created(
    state, session, test_app, db_user_1, permission_1, db_session_1, db_group_assigner, endpoint_user_group_create_permission_url
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
    state, session, test_app, db_user_1, permission_1, db_session_1, endpoint_user_group_create_permission_url
):
    response = await test_app.post(
        endpoint_user_group_create_permission_url,
        json={'permission_name': 'test_permission', **permission_1.as_dict()},
        headers={'Authorization': f'Bearer {db_session_1.token}'},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__create_group_permission__expired_session_nothing(
    state,
    session,
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
    state, session, test_app, db_user_1, db_permission_1, db_session_1, db_group_assigner, endpoint_user_group_create_url
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
    state, session, test_app, db_user_1, db_permission_1, db_session_1, endpoint_user_group_create_url
):
    response = await test_app.post(
        endpoint_user_group_create_url,
        json={'group_name': 'test_group', 'permissions': db_permission_1.name},
        headers={'Authorization': f'Bearer {db_session_1.token}'},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__create_group__expired_session_nothing(
    state, session, test_app, db_user_1, db_permission_1, db_expired_session_1, db_group_assigner, endpoint_user_group_create_url
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
    state, session, test_app, db_user_1, db_group_1, db_session_1, endpoint_user_group_join_url
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
    state, session, test_app, db_user_1, db_session_1, endpoint_user_group_join_url
):
    response = await test_app.post(
        endpoint_user_group_join_url,
        json={'group_name': 'nonexistent_group'},
        headers={'Authorization': f'Bearer {db_session_1.token}'},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__join_group__expired_session_nothing(
    state, session, test_app, db_user_1, db_group_1, db_expired_session_1, endpoint_user_group_join_url
):
    response = await test_app.post(
        endpoint_user_group_join_url,
        json={'group_name': db_group_1.name},
        headers={'Authorization': f'Bearer {db_expired_session_1.token}'},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test__leave_group__can_leave_group(
    state, session, test_app, db_user_1, db_group_1, db_session_1, endpoint_user_group_leave_url
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
    state, session, test_app, db_user_1, db_session_1, endpoint_user_group_leave_url
):
    response = await test_app.post(
        endpoint_user_group_leave_url,
        json={'group_name': 'nonexistent_group'},
        headers={'Authorization': f'Bearer {db_session_1.token}'},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__leave_group__expired_session_nothing(
    state, session, test_app, db_user_1, db_group_1, db_expired_session_1, endpoint_user_group_leave_url
):
    response = await test_app.post(
        endpoint_user_group_leave_url,
        json={'group_name': db_group_1.name},
        headers={'Authorization': f'Bearer {db_expired_session_1.token}'},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test__login_discord_redirect__returns_html(state, session, test_app, oauth_code_1, oauth_state_1):
    """Test that Discord OAuth redirect endpoint returns HTML response"""
    response = await test_app.get(f'/auth/login/discord?code={oauth_code_1}&state={oauth_state_1}')
    assert response.status_code == 200
    assert response.content_type.startswith('text/html')


@pytest.mark.asyncio
async def test__login_discord_redirect__handles_missing_code(state, session, test_app, oauth_state_2):
    """Test that Discord OAuth redirect endpoint handles missing code parameter"""
    # Should still return 200 but store empty code
    response = await test_app.get(f'/auth/login/discord?state={oauth_state_2}')
    assert response.status_code == 200


@pytest.mark.asyncio
async def test__login_discord__creates_session_for_existing_user(
    mocker,
    state,
    session,
    test_app,
    db_discord_user_1,
    discord_id_1,
    token_1,
    expire_valid,
    discord_token_1,
    make_mock_discord_response,
):
    """Test that Discord login creates a session for an existing Discord user"""
    mock_response = make_mock_discord_response(discord_id_1)

    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    mocker.patch('bw.models.auth.Session.human_session_length', return_value=expire_valid)
    mocker.patch('bw.auth.api.ENVIRONMENT.discord_api_url', return_value='https://discord.com/api')
    mocker.patch('aiohttp.ClientSession.get', return_value=mock_response)

    response = await test_app.post('/api/v1/auth/login/discord', headers={'Authorization': f'Bearer {discord_token_1}'})

    assert response.status_code == 200
    data = await response.get_json()
    assert 'session_token' in data
    assert 'expire_time' in data


@pytest.mark.asyncio
async def test__login_discord__creates_new_user_for_new_discord_id(
    mocker, state, session, test_app, token_1, expire_valid, discord_token_2, new_discord_id, make_mock_discord_response
):
    """Test that Discord login creates a new user for a Discord ID that doesn't exist"""
    mock_response = make_mock_discord_response(new_discord_id)

    mocker.patch('secrets.token_urlsafe', return_value=token_1)
    mocker.patch('bw.models.auth.Session.human_session_length', return_value=expire_valid)
    mocker.patch('bw.auth.api.ENVIRONMENT.discord_api_url', return_value='https://discord.com/api')
    mocker.patch('aiohttp.ClientSession.get', return_value=mock_response)

    response = await test_app.post('/api/v1/auth/login/discord', headers={'Authorization': f'Bearer {discord_token_2}'})

    assert response.status_code == 200
    data = await response.get_json()
    assert 'session_token' in data
    assert 'expire_time' in data


@pytest.mark.asyncio
async def test__login_discord__returns_401_for_invalid_token(
    mocker, state, session, test_app, discord_id_1, invalid_discord_token, make_mock_discord_response
):
    """Test that Discord login returns 401 for invalid Discord token"""
    mock_response = make_mock_discord_response(discord_id=discord_id_1, should_raise=True, error_status=401)

    mocker.patch('bw.auth.api.ENVIRONMENT.discord_api_url', return_value='https://discord.com/api')
    mocker.patch('aiohttp.ClientSession.post', return_value=mock_response)

    response = await test_app.post('/api/v1/auth/login/discord', headers={'Authorization': f'Bearer {invalid_discord_token}'})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test__login_discord__requires_authorization_header(state, session, test_app):
    response = await test_app.post('/api/v1/auth/login/discord')
    assert response.status_code == 401
