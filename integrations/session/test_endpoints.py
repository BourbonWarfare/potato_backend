# ruff: noqa: F811, F401

from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from bw.auth.roles import Roles
from bw.auth.user import UserStore
from bw.response import Created, JsonResponse, Ok
from integrations.auth.fixtures import db_expired_session_1, db_session_1, db_user_1, expire_invalid, token_1
from integrations.fixtures import test_app


@pytest.fixture(scope='session')
def session_id_1():
    return UUID('10000000-0000-0000-0000-000000000001')


@pytest.fixture(scope='session')
def endpoint_session_base_url():
    return '/api/v1/session'


@pytest.fixture(scope='session')
def endpoint_session_register_url(endpoint_session_base_url):
    return f'{endpoint_session_base_url}/register'


@pytest.fixture(scope='session')
def endpoint_session_finish_url(endpoint_session_base_url):
    return f'{endpoint_session_base_url}/finish'


@pytest.fixture(scope='session')
def endpoint_session_current_url(endpoint_session_base_url):
    return f'{endpoint_session_base_url}/current'


@pytest.fixture(scope='session')
def endpoint_session_finish_mission_url(endpoint_session_base_url):
    return f'{endpoint_session_base_url}/mission/finish'


@pytest.fixture(scope='session')
def endpoint_session_safe_start_disabled_url(endpoint_session_base_url):
    return f'{endpoint_session_base_url}/mission/safeStart/disabled'


@pytest.fixture(scope='session')
def can_manage_session_role_name():
    return 'session manager'


@pytest.fixture(scope='session')
def can_manage_session_role():
    return Roles(can_manage_session=True)


@pytest.fixture(scope='session')
def mission_name_with_version_1():
    return 'co10_test_v1'


@pytest.fixture(scope='session')
def mission_map_1():
    return 'Altis'


@pytest.fixture(scope='session')
def orbat_individual_json_1():
    return {'variable': 'u1', 'name': 'Player 1', 'is_member': True, 'rank': 1, 'steam_id': '1'}


@pytest.fixture(scope='session')
def orbat_json_above_cutoff(orbat_individual_json_1):
    return {'groups': [{'name': 'Alpha', 'side': 'WEST', 'leader': 'u1', 'members': [orbat_individual_json_1]}]}


@pytest.fixture(scope='session')
def orbat_json_below_cutoff():
    return {'groups': []}


@pytest.fixture(scope='function')
def db_can_manage_session_role(state, can_manage_session_role_name, can_manage_session_role):
    role = UserStore().create_role(state, can_manage_session_role_name, can_manage_session_role)
    yield role


@pytest.fixture(scope='function')
def db_user_1_can_manage_session(state, db_user_1, db_can_manage_session_role):
    UserStore().assign_user_role(state, db_user_1, db_can_manage_session_role.name)
    yield db_user_1


@pytest.fixture(scope='session')
def auth_headers_1(token_1):
    return {'Authorization': f'Bearer {token_1}'}


@pytest.fixture(scope='function')
def finish_mission_payload(session_id_1, mission_name_with_version_1, mission_map_1, orbat_json_above_cutoff):
    return {
        'session_id': str(session_id_1),
        'mission_name_with_version': mission_name_with_version_1,
        'mission_map': mission_map_1,
        'starting_orbat': orbat_json_above_cutoff,
        'final_orbat': orbat_json_above_cutoff,
    }


@pytest.fixture(scope='function')
def safe_start_payload(session_id_1, mission_name_with_version_1, mission_map_1, orbat_json_above_cutoff):
    return {
        'session_id': str(session_id_1),
        'mission_name_with_version': mission_name_with_version_1,
        'mission_map': mission_map_1,
        'orbat': orbat_json_above_cutoff,
    }


@pytest.mark.asyncio
async def test__register__success(
    test_app, mocker, db_session_1, db_user_1_can_manage_session, endpoint_session_register_url, auth_headers_1
):
    """Test that POST /session/register succeeds for a session manager."""
    # Not yet reviewed
    mocker.patch(
        'bw.session.endpoints.SessionApi.register', new_callable=AsyncMock, return_value=JsonResponse({'id': 'session-id'})
    )

    response = await test_app.post(endpoint_session_register_url, headers=auth_headers_1)

    assert response.status_code == 200
    data = await response.get_json()
    assert 'id' in data


@pytest.mark.asyncio
async def test__register__needs_role(test_app, db_session_1, endpoint_session_register_url, auth_headers_1):
    """Test that POST /session/register requires the session manager role."""
    # Not yet reviewed
    response = await test_app.post(endpoint_session_register_url, headers=auth_headers_1)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test__register__requires_authentication(test_app, endpoint_session_register_url):
    """Test that POST /session/register requires authentication."""
    # Not yet reviewed
    response = await test_app.post(endpoint_session_register_url)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test__register__rejects_expired_session(
    test_app, db_expired_session_1, db_user_1_can_manage_session, endpoint_session_register_url, auth_headers_1
):
    """Test that POST /session/register rejects expired sessions."""
    # Not yet reviewed
    response = await test_app.post(endpoint_session_register_url, headers=auth_headers_1)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test__finish__success(
    test_app, mocker, db_session_1, db_user_1_can_manage_session, endpoint_session_finish_url, auth_headers_1, session_id_1
):
    """Test that POST /session/finish succeeds for a session manager."""
    # Not yet reviewed
    finish = mocker.patch('bw.session.endpoints.SessionApi.finish', new_callable=AsyncMock, return_value=Ok())

    response = await test_app.post(endpoint_session_finish_url, headers=auth_headers_1, json={'session_id': str(session_id_1)})

    assert response.status_code == 200
    finish.assert_called_once()


@pytest.mark.asyncio
async def test__finish__needs_role(test_app, db_session_1, endpoint_session_finish_url, auth_headers_1, session_id_1):
    """Test that POST /session/finish requires the session manager role."""
    # Not yet reviewed
    response = await test_app.post(endpoint_session_finish_url, headers=auth_headers_1, json={'session_id': str(session_id_1)})

    assert response.status_code == 403


@pytest.mark.asyncio
async def test__finish__needs_uuid(
    test_app, db_session_1, db_user_1_can_manage_session, endpoint_session_finish_url, auth_headers_1
):
    """Test that POST /session/finish requires a valid UUID."""
    # Not yet reviewed
    response = await test_app.post(endpoint_session_finish_url, headers=auth_headers_1, json={'session_id': 'not-a-uuid'})

    assert response.status_code >= 400


@pytest.mark.asyncio
async def test__finish__requires_authentication(test_app, endpoint_session_finish_url, session_id_1):
    """Test that POST /session/finish requires authentication."""
    # Not yet reviewed
    response = await test_app.post(endpoint_session_finish_url, json={'session_id': str(session_id_1)})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test__get_current__success(
    test_app, mocker, db_session_1, db_user_1_can_manage_session, endpoint_session_current_url, auth_headers_1
):
    """Test that GET /session/current succeeds for a session manager."""
    # Not yet reviewed
    mocker.patch(
        'bw.session.endpoints.SessionApi.get_latest_session',
        new_callable=AsyncMock,
        return_value=JsonResponse({'id': 'session-id'}),
    )

    response = await test_app.get(endpoint_session_current_url, headers=auth_headers_1)

    assert response.status_code == 200
    data = await response.get_json()
    assert 'id' in data


@pytest.mark.asyncio
async def test__get_current__needs_role(test_app, db_session_1, endpoint_session_current_url, auth_headers_1):
    """Test that GET /session/current requires the session manager role."""
    # Not yet reviewed
    response = await test_app.get(endpoint_session_current_url, headers=auth_headers_1)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test__finish_mission__success(
    test_app,
    mocker,
    db_session_1,
    db_user_1_can_manage_session,
    endpoint_session_finish_mission_url,
    auth_headers_1,
    finish_mission_payload,
):
    """Test that POST /session/mission/finish succeeds for a session manager."""
    # Not yet reviewed
    finish_mission = mocker.patch(
        'bw.session.endpoints.SessionApi.finish_mission', new_callable=AsyncMock, return_value=Created()
    )

    response = await test_app.post(endpoint_session_finish_mission_url, headers=auth_headers_1, json=finish_mission_payload)

    assert response.status_code == 201
    finish_mission.assert_called_once()


@pytest.mark.asyncio
async def test__finish_mission__needs_role(
    test_app, db_session_1, endpoint_session_finish_mission_url, auth_headers_1, finish_mission_payload
):
    """Test that POST /session/mission/finish requires the session manager role."""
    # Not yet reviewed
    response = await test_app.post(endpoint_session_finish_mission_url, headers=auth_headers_1, json=finish_mission_payload)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test__finish_mission__needs_mission_information(
    test_app, db_session_1, db_user_1_can_manage_session, endpoint_session_finish_mission_url, auth_headers_1, session_id_1
):
    """Test that POST /session/mission/finish requires mission information."""
    # Not yet reviewed
    response = await test_app.post(
        endpoint_session_finish_mission_url, headers=auth_headers_1, json={'session_id': str(session_id_1)}
    )

    assert response.status_code >= 400


@pytest.mark.asyncio
async def test__safe_start_disabled__success(
    test_app,
    mocker,
    db_session_1,
    db_user_1_can_manage_session,
    endpoint_session_safe_start_disabled_url,
    auth_headers_1,
    safe_start_payload,
):
    """Test that POST /session/mission/safeStart/disabled succeeds for a session manager."""
    # Not yet reviewed
    safe_start_ended = mocker.patch(
        'bw.session.endpoints.SessionApi.safe_start_ended', new_callable=AsyncMock, return_value=Created()
    )

    response = await test_app.post(endpoint_session_safe_start_disabled_url, headers=auth_headers_1, json=safe_start_payload)

    assert response.status_code == 201
    safe_start_ended.assert_called_once()


@pytest.mark.asyncio
async def test__safe_start_disabled__needs_role(
    test_app, db_session_1, endpoint_session_safe_start_disabled_url, auth_headers_1, safe_start_payload
):
    """Test that POST /session/mission/safeStart/disabled requires the session manager role."""
    # Not yet reviewed
    response = await test_app.post(endpoint_session_safe_start_disabled_url, headers=auth_headers_1, json=safe_start_payload)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test__safe_start_disabled__requires_authentication(
    test_app, endpoint_session_safe_start_disabled_url, safe_start_payload
):
    """Test that POST /session/mission/safeStart/disabled requires authentication."""
    # Not yet reviewed
    response = await test_app.post(endpoint_session_safe_start_disabled_url, json=safe_start_payload)

    assert response.status_code == 401
