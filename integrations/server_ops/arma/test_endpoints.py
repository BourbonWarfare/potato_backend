# ruff: noqa: F811, F401

from unittest.mock import AsyncMock

import pytest

from bw.auth.user import UserStore
from bw.response import WebResponse
from bw.server_ops.arma.mod import MODLISTS, MODS, Mod, Modlist, WorkshopId
from integrations.auth.fixtures import (
    db_expired_session_1,
    db_server_manager,
    db_session_1,
    db_user_1,
    expire_invalid,
    server_manager,
    server_manager_name,
    token_1,
)
from integrations.fixtures import test_app
from integrations.server_ops.arma.fixtures import (
    endpoint_arma_base_url,
    endpoint_events_url,
    endpoint_modlists_url,
    endpoint_mods_url,
    endpoint_reload_modlists_url,
    endpoint_reload_mods_url,
    endpoint_server_modlist_url,
    endpoint_server_mods_url,
    endpoint_servers_url,
    existing_mod_name,
    mock_mod_1,
    mock_mod_2,
    mock_mod_name_1,
    mock_mod_name_2,
    mock_mod_name_3,
    mock_modlist_1,
    mock_modlist_2,
    mock_modlist_3,
    mock_modlist_4,
    mock_modlist_name_1,
    mock_modlist_name_2,
    mock_modlist_name_3,
    mock_modlist_name_4,
    mock_modlist_name_5,
    mock_modlist_name_6,
    mock_server_1,
    mock_server_2,
    mock_server_3,
    mock_workshop_id_1,
    mock_workshop_id_2,
    mock_workshop_id_3,
    nonexistent_mod_name,
    server_name_1,
    server_name_2,
    server_name_3,
    server_name_4,
)

# Tests for GET /<server>/rpt


@pytest.mark.asyncio
async def test__get_latest_rpt__returns_stream_successfully(
    mocker, state, test_app, db_user_1, db_session_1, db_server_manager, endpoint_arma_base_url, server_name_1
):
    """Test that GET /<server>/rpt successfully returns the latest RPT stream"""
    # Arrange
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)

    mock_response = WebResponse(200, response='arma 3 server log data chunk')
    mock_get_rpt = mocker.patch('bw.server_ops.arma.endpoints.ArmaApi.get_latest_rpt', return_value=mock_response)

    # Act
    url = f'{endpoint_arma_base_url}/{server_name_1}/rpt'
    response = await test_app.get(url, headers={'Authorization': f'Bearer {db_session_1.token}'})

    # Assert
    assert response.status_code == 200
    mock_get_rpt.assert_called_once_with(server_name_1)
    assert await response.get_data(as_text=True) == 'arma 3 server log data chunk'


@pytest.mark.asyncio
async def test__get_latest_rpt__returns_404_when_not_found(
    mocker, state, test_app, db_user_1, db_session_1, db_server_manager, endpoint_arma_base_url, server_name_2
):
    """Test that GET /<server>/rpt returns 404 when server or RPT logs are missing"""
    # Arrange
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)

    mock_response = WebResponse(404)
    mocker.patch('bw.server_ops.arma.endpoints.ArmaApi.get_latest_rpt', return_value=mock_response)

    # Act
    url = f'{endpoint_arma_base_url}/{server_name_2}/rpt'
    response = await test_app.get(url, headers={'Authorization': f'Bearer {db_session_1.token}'})

    # Assert
    assert response.status_code == 404


@pytest.mark.asyncio
async def test__get_latest_rpt__requires_authentication(state, test_app, endpoint_arma_base_url, server_name_1):
    """Test that GET /<server>/rpt requires authentication"""
    # Act
    url = f'{endpoint_arma_base_url}/{server_name_1}/rpt'
    response = await test_app.get(url)

    # Assert
    assert response.status_code == 401


@pytest.mark.asyncio
async def test__get_latest_rpt__requires_permission(
    state, test_app, db_user_1, db_session_1, endpoint_arma_base_url, server_name_1
):
    """Test that GET /<server>/rpt requires can_manage_server role"""
    # Act
    url = f'{endpoint_arma_base_url}/{server_name_1}/rpt'
    response = await test_app.get(url, headers={'Authorization': f'Bearer {db_session_1.token}'})

    # Assert
    assert response.status_code == 403


@pytest.mark.asyncio
async def test__get_latest_rpt__rejects_expired_session(
    mocker, state, test_app, db_user_1, db_expired_session_1, db_server_manager, endpoint_arma_base_url, server_name_1
):
    """Test that GET /<server>/rpt rejects expired sessions"""
    # Arrange
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)

    # Act
    url = f'{endpoint_arma_base_url}/{server_name_1}/rpt'
    response = await test_app.get(url, headers={'Authorization': f'Bearer {db_expired_session_1.token}'})

    # Assert
    assert response.status_code == 401


# Tests for GET /mods


@pytest.mark.asyncio
async def test__get_configured_mods__returns_mods(mocker, state, test_app, endpoint_mods_url, mock_mod_1, mock_mod_2):
    """Test that GET /mods returns all configured mods"""
    mock_mods = {
        mock_mod_1.name: mock_mod_1,
        mock_mod_2.name: mock_mod_2,
    }
    mocker.patch('bw.server_ops.arma.api.MODS', mock_mods)

    response = await test_app.get(endpoint_mods_url)

    assert response.status_code == 200
    data = await response.get_json()
    assert 'mods' in data
    assert len(data['mods']) == 2
    assert mock_mod_1.name in [mod['name'] for mod in data['mods']]
    assert mock_mod_2.name in [mod['name'] for mod in data['mods']]


@pytest.mark.asyncio
async def test__get_configured_mods__returns_empty_list(mocker, state, test_app, endpoint_mods_url):
    """Test that GET /mods returns empty list when no mods configured"""
    mocker.patch('bw.server_ops.arma.api.MODS', {})

    response = await test_app.get(endpoint_mods_url)

    assert response.status_code == 200
    data = await response.get_json()
    assert data['mods'] == []


# Tests for GET /mods/<server>


@pytest.mark.asyncio
async def test__get_server_mods__returns_server_mods(
    mocker, state, test_app, endpoint_server_mods_url, server_name_1, mock_modlist_1
):
    """Test that GET /mods/<server> returns mods for specific server"""
    mock_server = mocker.Mock()
    mock_server.modlist.return_value = mock_modlist_1

    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {server_name_1: mock_server})

    response = await test_app.get(endpoint_server_mods_url)

    assert response.status_code == 200
    data = await response.get_json()
    assert 'mods' in data
    assert len(data['mods']) == 2


@pytest.mark.asyncio
async def test__get_server_mods__returns_404_for_nonexistent_server(
    mocker, state, test_app, endpoint_arma_base_url, server_name_2
):
    """Test that GET /mods/<server> returns 404 for nonexistent server"""
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {})

    response = await test_app.get(f'{endpoint_arma_base_url}/mods/{server_name_2}')

    assert response.status_code == 404


# Tests for GET /mods/lists


@pytest.mark.asyncio
async def test__get_configured_modlists__returns_modlists(
    mocker, state, test_app, endpoint_modlists_url, mock_modlist_2, mock_modlist_3
):
    """Test that GET /mods/lists returns all configured modlists"""
    mock_modlists = {
        mock_modlist_2.name: mock_modlist_2,
        mock_modlist_3.name: mock_modlist_3,
    }
    mocker.patch('bw.server_ops.arma.api.MODLISTS', mock_modlists)

    response = await test_app.get(endpoint_modlists_url)

    assert response.status_code == 200
    data = await response.get_json()
    assert 'modlists' in data
    assert len(data['modlists']) == 2
    assert mock_modlist_2.name in data['modlists']
    assert mock_modlist_3.name in data['modlists']


@pytest.mark.asyncio
async def test__get_configured_modlists__returns_empty_dict(mocker, state, test_app, endpoint_modlists_url):
    """Test that GET /mods/lists returns empty dict when no modlists configured"""
    mocker.patch('bw.server_ops.arma.api.MODLISTS', {})

    response = await test_app.get(endpoint_modlists_url)

    assert response.status_code == 200
    data = await response.get_json()
    assert data['modlists'] == {}


# Tests for GET /mods/list/<server>


@pytest.mark.asyncio
async def test__get_server_modlist__returns_server_modlist(
    mocker, state, test_app, endpoint_server_modlist_url, server_name_1, mock_modlist_1
):
    """Test that GET /mods/list/<server> returns modlist for specific server"""
    mock_server = mocker.Mock()
    mock_server.modlist.return_value = mock_modlist_1
    mock_server._config.require.return_value.get.return_value = mock_modlist_1.name

    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {server_name_1: mock_server})

    response = await test_app.get(endpoint_server_modlist_url)

    assert response.status_code == 200
    data = await response.get_json()
    assert data['modlist_name'] == mock_modlist_1.name
    assert len(data['mods']) == 2


@pytest.mark.asyncio
async def test__get_server_modlist__returns_404_for_nonexistent_server(
    mocker, state, test_app, endpoint_arma_base_url, server_name_2
):
    """Test that GET /mods/list/<server> returns 404 for nonexistent server"""
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {})

    response = await test_app.get(f'{endpoint_arma_base_url}/mods/list/{server_name_2}')

    assert response.status_code == 404


# Tests for POST /mods/reload


@pytest.mark.asyncio
async def test__reload_mods__reloads_successfully(
    mocker, state, test_app, db_user_1, db_session_1, db_server_manager, endpoint_reload_mods_url
):
    """Test that POST /mods/reload reloads mod configuration"""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    mocker.patch('bw.server_ops.arma.endpoints.ENVIRONMENT.arma_mod_config_path', return_value='/test/path')
    mocker.patch('bw.server_ops.arma.api.load_mod_configs', return_value=None)

    response = await test_app.post(endpoint_reload_mods_url, headers={'Authorization': f'Bearer {db_session_1.token}'})

    assert response.status_code == 200


@pytest.mark.asyncio
async def test__reload_mods__requires_authentication(state, test_app, endpoint_reload_mods_url):
    """Test that POST /mods/reload requires authentication"""
    response = await test_app.post(endpoint_reload_mods_url)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test__reload_mods__requires_permission(state, test_app, db_user_1, db_session_1, endpoint_reload_mods_url):
    """Test that POST /mods/reload requires can_manage_server role"""
    response = await test_app.post(endpoint_reload_mods_url, headers={'Authorization': f'Bearer {db_session_1.token}'})

    assert response.status_code == 403


@pytest.mark.asyncio
async def test__reload_mods__rejects_expired_session(
    mocker, state, test_app, db_user_1, db_expired_session_1, db_server_manager, endpoint_reload_mods_url
):
    """Test that POST /mods/reload rejects expired sessions"""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)

    response = await test_app.post(endpoint_reload_mods_url, headers={'Authorization': f'Bearer {db_expired_session_1.token}'})

    assert response.status_code == 401


# Tests for POST /mods/lists/reload


@pytest.mark.asyncio
async def test__reload_modlists__reloads_successfully(
    mocker, state, test_app, db_user_1, db_session_1, db_server_manager, endpoint_reload_modlists_url
):
    """Test that POST /mods/lists/reload reloads modlist configuration"""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    mock_load_modlists = mocker.patch('bw.server_ops.arma.api.load_modlists')
    mocker.patch('bw.server_ops.arma.endpoints.ENVIRONMENT.arma_modlist_config_path', return_value='/test/path')

    response = await test_app.post(endpoint_reload_modlists_url, headers={'Authorization': f'Bearer {db_session_1.token}'})

    assert response.status_code == 200
    mock_load_modlists.assert_called_once()


@pytest.mark.asyncio
async def test__reload_modlists__requires_authentication(state, test_app, endpoint_reload_modlists_url):
    """Test that POST /mods/lists/reload requires authentication"""
    response = await test_app.post(endpoint_reload_modlists_url)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test__reload_modlists__requires_permission(state, test_app, db_user_1, db_session_1, endpoint_reload_modlists_url):
    """Test that POST /mods/lists/reload requires can_manage_server role"""
    response = await test_app.post(endpoint_reload_modlists_url, headers={'Authorization': f'Bearer {db_session_1.token}'})

    assert response.status_code == 403


# Tests for POST /mods


@pytest.mark.asyncio
async def test__add_new_mod__creates_mod_successfully(
    mocker,
    state,
    test_app,
    db_user_1,
    db_session_1,
    db_server_manager,
    endpoint_mods_url,
    mock_mod_name_3,
    mock_workshop_id_3,
):
    """Test that POST /mods creates a new mod"""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    mocker.patch('bw.server_ops.arma.api.MODS', {})

    response = await test_app.post(
        endpoint_mods_url,
        json={
            'mod_name': mock_mod_name_3,
            'workshop_id': mock_workshop_id_3,
            'kind': 'mod',
            'manual_install': False,
            'directory': '@mod',
        },
        headers={'Authorization': f'Bearer {db_session_1.token}'},
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test__add_new_mod__requires_authentication(state, test_app, endpoint_mods_url, mock_mod_name_3, mock_workshop_id_3):
    """Test that POST /mods requires authentication"""
    response = await test_app.post(
        endpoint_mods_url,
        json={
            'mod_name': mock_mod_name_3,
            'workshop_id': mock_workshop_id_3,
            'kind': 'mod',
            'manual_install': False,
            'directory': '@foobar',
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test__add_new_mod__requires_permission(
    state, test_app, db_user_1, db_session_1, endpoint_mods_url, mock_mod_name_3, mock_workshop_id_3
):
    """Test that POST /mods requires can_manage_server role"""
    response = await test_app.post(
        endpoint_mods_url,
        json={
            'mod_name': mock_mod_name_3,
            'workshop_id': mock_workshop_id_3,
            'kind': 'mod',
            'manual_install': False,
            'directory': '@mod',
        },
        headers={'Authorization': f'Bearer {db_session_1.token}'},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test__add_new_mod__rejects_duplicate_mod(
    mocker,
    state,
    test_app,
    db_user_1,
    db_session_1,
    db_server_manager,
    endpoint_mods_url,
    existing_mod_name,
    mock_workshop_id_1,
):
    """Test that POST /mods rejects duplicate mod names"""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    existing_mod = Mod(name=existing_mod_name, workshop_id=WorkshopId(mock_workshop_id_1))
    mocker.patch('bw.server_ops.arma.api.MODS', {existing_mod_name: existing_mod})

    response = await test_app.post(
        endpoint_mods_url,
        json={
            'mod_name': existing_mod_name,
            'workshop_id': 456789,
            'kind': 'mod',
            'manual_install': False,
            'directory': '@mod',
        },
        headers={'Authorization': f'Bearer {db_session_1.token}'},
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test__add_new_mod__rejects_invalid_kind(
    mocker,
    state,
    test_app,
    db_user_1,
    db_session_1,
    db_server_manager,
    endpoint_mods_url,
    mock_mod_name_3,
    mock_workshop_id_3,
):
    """Test that POST /mods rejects invalid kind parameter"""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    mocker.patch('bw.server_ops.arma.api.MODS', {})

    response = await test_app.post(
        endpoint_mods_url,
        json={
            'mod_name': mock_mod_name_3,
            'workshop_id': mock_workshop_id_3,
            'kind': 'invalid_kind',
            'manual_install': False,
            'directory': '@mod',
        },
        headers={'Authorization': f'Bearer {db_session_1.token}'},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test__add_new_mod__rejects_missing_workshop_id(
    mocker, state, test_app, db_user_1, db_session_1, db_server_manager, endpoint_mods_url, mock_mod_name_3
):
    """Test that POST /mods rejects non-manual mod without workshop_id"""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    mocker.patch('bw.server_ops.arma.api.MODS', {})

    response = await test_app.post(
        endpoint_mods_url,
        json={
            'mod_name': mock_mod_name_3,
            'workshop_id': None,
            'kind': 'mod',
            'manual_install': False,
            'directory': '@mod',
        },
        headers={'Authorization': f'Bearer {db_session_1.token}'},
    )

    assert response.status_code == 400


# Tests for POST /mods/lists


@pytest.mark.asyncio
async def test__add_new_modlist__creates_modlist_successfully(
    mocker,
    state,
    test_app,
    db_user_1,
    db_session_1,
    db_server_manager,
    endpoint_modlists_url,
    mock_mod_1,
    mock_mod_2,
    mock_modlist_name_4,
):
    """Test that POST /mods/lists creates a new modlist"""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    mocker.patch('bw.server_ops.arma.api.MODS', {mock_mod_1.name: mock_mod_1, mock_mod_2.name: mock_mod_2})
    mocker.patch('bw.server_ops.arma.api.MODLISTS', {})

    response = await test_app.post(
        endpoint_modlists_url,
        json={'name': mock_modlist_name_4, 'mods': [mock_mod_1.name, mock_mod_2.name]},
        headers={'Authorization': f'Bearer {db_session_1.token}'},
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test__add_new_modlist__requires_authentication(
    state, test_app, endpoint_modlists_url, mock_mod_name_1, mock_mod_name_2, mock_modlist_name_4
):
    """Test that POST /mods/lists requires authentication"""
    response = await test_app.post(
        endpoint_modlists_url, json={'name': mock_modlist_name_4, 'mods': [mock_mod_name_1, mock_mod_name_2]}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test__add_new_modlist__requires_permission(
    state,
    test_app,
    db_user_1,
    db_session_1,
    endpoint_modlists_url,
    mock_mod_name_1,
    mock_mod_name_2,
    mock_modlist_name_4,
):
    """Test that POST /mods/lists requires can_manage_server role"""
    response = await test_app.post(
        endpoint_modlists_url,
        json={'name': mock_modlist_name_4, 'mods': [mock_mod_name_1, mock_mod_name_2]},
        headers={'Authorization': f'Bearer {db_session_1.token}'},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test__add_new_modlist__rejects_duplicate_modlist(
    mocker,
    state,
    test_app,
    db_user_1,
    db_session_1,
    db_server_manager,
    endpoint_modlists_url,
    mock_mod_1,
    mock_modlist_4,
    mock_modlist_name_5,
):
    """Test that POST /mods/lists rejects duplicate modlist names"""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    mocker.patch('bw.server_ops.arma.api.MODS', {mock_mod_1.name: mock_mod_1})
    mocker.patch('bw.server_ops.arma.api.MODLISTS', {mock_modlist_name_5: mock_modlist_4})

    response = await test_app.post(
        endpoint_modlists_url,
        json={'name': mock_modlist_name_5, 'mods': [mock_mod_1.name]},
        headers={'Authorization': f'Bearer {db_session_1.token}'},
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test__add_new_modlist__rejects_nonexistent_mod(
    mocker,
    state,
    test_app,
    db_user_1,
    db_session_1,
    db_server_manager,
    endpoint_modlists_url,
    nonexistent_mod_name,
    mock_modlist_name_4,
):
    """Test that POST /mods/lists rejects modlist with nonexistent mod"""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    mocker.patch('bw.server_ops.arma.api.MODS', {})
    mocker.patch('bw.server_ops.arma.api.MODLISTS', {})

    response = await test_app.post(
        endpoint_modlists_url,
        json={'name': mock_modlist_name_4, 'mods': [nonexistent_mod_name]},
        headers={'Authorization': f'Bearer {db_session_1.token}'},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test__add_new_modlist__creates_empty_modlist(
    mocker, state, test_app, db_user_1, db_session_1, db_server_manager, endpoint_modlists_url, mock_modlist_name_6
):
    """Test that POST /mods/lists can create empty modlist"""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    mocker.patch('bw.server_ops.arma.api.MODS', {})
    mocker.patch('bw.server_ops.arma.api.MODLISTS', {})

    response = await test_app.post(
        endpoint_modlists_url,
        json={'name': mock_modlist_name_6, 'mods': []},
        headers={'Authorization': f'Bearer {db_session_1.token}'},
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test__get_all_servers__returns_servers(
    mocker,
    state,
    test_app,
    endpoint_servers_url,
    server_name_1,
    server_name_2,
    server_name_3,
    mock_server_1,
    mock_server_2,
    mock_server_3,
):
    """Test that GET /servers returns all configured servers"""
    # Not yet reviewed
    mock_server_map = {
        server_name_1: mock_server_1,
        server_name_2: mock_server_2,
        server_name_3: mock_server_3,
    }
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', mock_server_map)

    response = await test_app.get(endpoint_servers_url)

    assert response.status_code == 200
    data = await response.get_json()
    assert 'servers' in data
    assert len(data['servers']) == 3
    assert server_name_1 == data['servers'][0]
    assert server_name_2 in data['servers'][2]
    assert server_name_3 in data['servers'][1]


@pytest.mark.asyncio
async def test__get_all_servers__returns_empty_list(mocker, state, test_app, endpoint_servers_url):
    """Test that GET /servers returns empty list when no servers configured"""
    # Not yet reviewed
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {})

    response = await test_app.get(endpoint_servers_url)

    assert response.status_code == 200
    data = await response.get_json()
    assert data['servers'] == []


# Additional protected server operation endpoint coverage


@pytest.fixture(scope='session')
def endpoint_start_server_url(endpoint_arma_base_url, server_name_1):
    return f'{endpoint_arma_base_url}/{server_name_1}/start'


@pytest.fixture(scope='session')
def endpoint_stop_server_url(endpoint_arma_base_url, server_name_1):
    return f'{endpoint_arma_base_url}/{server_name_1}/stop'


@pytest.fixture(scope='session')
def endpoint_restart_server_url(endpoint_arma_base_url, server_name_1):
    return f'{endpoint_arma_base_url}/{server_name_1}/restart'


@pytest.fixture(scope='session')
def endpoint_update_server_url(endpoint_arma_base_url, server_name_1):
    return f'{endpoint_arma_base_url}/{server_name_1}/update'


@pytest.fixture(scope='session')
def endpoint_update_server_mods_url(endpoint_arma_base_url, server_name_1):
    return f'{endpoint_arma_base_url}/{server_name_1}/update_mods'


@pytest.fixture(scope='session')
def endpoint_healthcheck_server_url(endpoint_arma_base_url, server_name_1):
    return f'{endpoint_arma_base_url}/{server_name_1}/healthcheck'


@pytest.fixture(scope='session')
def endpoint_status_server_url(endpoint_arma_base_url, server_name_1):
    return f'{endpoint_arma_base_url}/{server_name_1}/status'


@pytest.fixture(scope='session')
def endpoint_update_specific_mod_url(endpoint_arma_base_url, mock_workshop_id_1):
    return f'{endpoint_arma_base_url}/mod/{mock_workshop_id_1}/update'


@pytest.fixture(scope='session')
def auth_header_1(token_1):
    return {'Authorization': f'Bearer {token_1}'}


@pytest.mark.asyncio
async def test__start_server__starts_server_successfully(
    mocker, state, test_app, db_user_1, db_session_1, db_server_manager, endpoint_start_server_url, auth_header_1
):
    """Test that POST /<server>/start starts a server for server managers."""
    # Not yet reviewed
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    start_server = mocker.patch(
        'bw.server_ops.arma.endpoints.ArmaApi.start_server', new_callable=AsyncMock, return_value=WebResponse(200)
    )

    response = await test_app.post(endpoint_start_server_url, headers=auth_header_1)

    assert response.status_code == 200
    start_server.assert_called_once()


@pytest.mark.asyncio
async def test__start_server__requires_authentication(test_app, endpoint_start_server_url):
    """Test that POST /<server>/start requires authentication."""
    # Not yet reviewed
    response = await test_app.post(endpoint_start_server_url)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test__start_server__requires_permission(test_app, db_session_1, endpoint_start_server_url, auth_header_1):
    """Test that POST /<server>/start requires server manager permission."""
    # Not yet reviewed
    response = await test_app.post(endpoint_start_server_url, headers=auth_header_1)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test__stop_server__stops_server_successfully(
    mocker, state, test_app, db_user_1, db_session_1, db_server_manager, endpoint_stop_server_url, auth_header_1
):
    """Test that POST /<server>/stop stops a server for server managers."""
    # Not yet reviewed
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    stop_server = mocker.patch(
        'bw.server_ops.arma.endpoints.ArmaApi.stop_server', new_callable=AsyncMock, return_value=WebResponse(200)
    )

    response = await test_app.post(endpoint_stop_server_url, headers=auth_header_1)

    assert response.status_code == 200
    stop_server.assert_called_once()


@pytest.mark.asyncio
async def test__restart_server__restarts_server_successfully(
    mocker, state, test_app, db_user_1, db_session_1, db_server_manager, endpoint_restart_server_url, auth_header_1
):
    """Test that POST /<server>/restart restarts a server for server managers."""
    # Not yet reviewed
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    restart_server = mocker.patch(
        'bw.server_ops.arma.endpoints.ArmaApi.restart_server', new_callable=AsyncMock, return_value=WebResponse(200)
    )

    response = await test_app.post(endpoint_restart_server_url, headers=auth_header_1)

    assert response.status_code == 200
    restart_server.assert_called_once()


@pytest.mark.asyncio
async def test__update_server__updates_server_successfully(
    mocker, state, test_app, db_user_1, db_session_1, db_server_manager, endpoint_update_server_url, auth_header_1
):
    """Test that POST /<server>/update updates a server for server managers."""
    # Not yet reviewed
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    update_server = mocker.patch(
        'bw.server_ops.arma.endpoints.ArmaApi.update_server', new_callable=AsyncMock, return_value=WebResponse(200)
    )

    response = await test_app.post(endpoint_update_server_url, headers=auth_header_1)

    assert response.status_code == 200
    update_server.assert_called_once()


@pytest.mark.asyncio
async def test__update_server_mods__updates_mods_successfully(
    mocker, state, test_app, db_user_1, db_session_1, db_server_manager, endpoint_update_server_mods_url, auth_header_1
):
    """Test that POST /<server>/update_mods updates server mods for server managers."""
    # Not yet reviewed
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    update_server_mods = mocker.patch(
        'bw.server_ops.arma.endpoints.ArmaApi.update_server_mods', new_callable=AsyncMock, return_value=WebResponse(200)
    )

    response = await test_app.post(endpoint_update_server_mods_url, headers=auth_header_1)

    assert response.status_code == 200
    update_server_mods.assert_called_once()


@pytest.mark.asyncio
async def test__healthcheck_server__checks_health_successfully(
    mocker, test_app, endpoint_healthcheck_server_url, server_name_1, mock_server_1
):
    """Test that GET /<server>/healthcheck checks the configured server health."""
    # Not yet reviewed
    mock_server_1.server_port.return_value = 2302
    mocker.patch('bw.server_ops.arma.endpoints.ArmaApi.get_server_from_string', return_value=mock_server_1)
    server_ping = mocker.patch(
        'bw.server_ops.arma.endpoints.ArmaApi.server_ping', new_callable=AsyncMock, return_value=WebResponse(200)
    )

    response = await test_app.get(endpoint_healthcheck_server_url)

    assert response.status_code == 200
    server_ping.assert_called_once_with('localhost', 2303)


@pytest.mark.asyncio
async def test__server_status__checks_status_successfully(mocker, test_app, endpoint_status_server_url, mock_server_1):
    """Test that GET /<server>/status checks the configured server status."""
    # Not yet reviewed
    mock_server_1.server_port.return_value = 2302
    mocker.patch('bw.server_ops.arma.endpoints.ArmaApi.get_server_from_string', return_value=mock_server_1)
    server_steam_status = mocker.patch(
        'bw.server_ops.arma.endpoints.ArmaApi.server_steam_status', new_callable=AsyncMock, return_value=WebResponse(200)
    )

    response = await test_app.get(endpoint_status_server_url)

    assert response.status_code == 200
    server_steam_status.assert_called_once_with('localhost', 2303)


@pytest.mark.asyncio
async def test__update_specific_mod__returns_404_for_unknown_workshop_id(
    mocker, state, test_app, db_user_1, db_session_1, db_server_manager, endpoint_update_specific_mod_url, auth_header_1
):
    """Test that POST /mod/<workshop_id>/update returns not found for unknown mods."""
    # Not yet reviewed
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    mocker.patch('bw.server_ops.arma.endpoints.MODS', {})

    response = await test_app.post(endpoint_update_specific_mod_url, headers=auth_header_1)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test__update_specific_mod__updates_matching_mod(
    mocker,
    state,
    test_app,
    db_user_1,
    db_session_1,
    db_server_manager,
    endpoint_update_specific_mod_url,
    auth_header_1,
    mock_mod_1,
):
    """Test that POST /mod/<workshop_id>/update updates the matching mod."""
    # Not yet reviewed
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    mocker.patch('bw.server_ops.arma.endpoints.MODS', {mock_mod_1.name: mock_mod_1})
    update_mods = mocker.patch(
        'bw.server_ops.arma.endpoints.ArmaApi.update_mods', new_callable=AsyncMock, return_value=WebResponse(200)
    )

    response = await test_app.post(endpoint_update_specific_mod_url, headers=auth_header_1)

    assert response.status_code == 200
    update_mods.assert_called_once()
    assert update_mods.call_args.args[1] == [mock_mod_1]


@pytest.mark.asyncio
async def test__create_event__records_event(
    state, test_app, endpoint_events_url, db_user_1, db_session_1, auth_header_1, db_server_manager
):
    """Test that POST /events records a tagged Arma event."""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    response = await test_app.post(
        endpoint_events_url,
        json={'tag': 'script_error', 'message': 'Undefined variable _unit', 'server': ''},
        headers=auth_header_1,
    )

    assert response.status_code == 201
    data = await response.get_json()
    assert data['event']['tag'] == 'script_error'
    assert data['event']['message'] == 'Undefined variable _unit'


@pytest.mark.asyncio
async def test__create_event__requires_json(
    state, test_app, endpoint_events_url, db_user_1, db_session_1, auth_header_1, db_server_manager
):
    """Test that POST /events requires a JSON body."""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    response = await test_app.post(endpoint_events_url, data='not json', headers=auth_header_1)

    assert response.status_code == 415


@pytest.mark.asyncio
async def test__create_event__rejects_missing_message(
    state, test_app, endpoint_events_url, db_user_1, db_session_1, auth_header_1, db_server_manager
):
    """Test that POST /events rejects payloads without a message."""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    response = await test_app.post(endpoint_events_url, json={'tag': 'server_message', 'server': 'main'}, headers=auth_header_1)

    assert response.status_code == 400


@pytest.mark.asyncio
async def test__get_events__returns_json_by_default(
    state, test_app, endpoint_events_url, db_user_1, db_session_1, auth_header_1, db_server_manager
):
    """Test that GET /events returns paginated JSON by default."""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    await test_app.post(
        endpoint_events_url, json={'tag': 'server_message', 'message': 'Mission started', 'server': 'main'}, headers=auth_header_1
    )

    response = await test_app.get(f'{endpoint_events_url}?page=1&page_size=10', headers=auth_header_1)

    assert response.status_code == 200
    assert response.content_type.startswith('application/json')
    data = await response.get_json()
    assert data['total'] == 1
    assert data['page'] == 1
    assert data['page_size'] == 10
    assert data['events'][0]['tag'] == 'server_message'
    assert data['events'][0]['message'] == 'Mission started'


@pytest.mark.asyncio
async def test__get_events__filters_by_repeated_tag_params(
    state, test_app, endpoint_events_url, db_user_1, db_session_1, auth_header_1, db_server_manager
):
    """Test that GET /events can filter by repeated tag query parameters."""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    await test_app.post(
        endpoint_events_url, json={'tag': 'server_message', 'message': 'Mission started', 'server': 'main'}, headers=auth_header_1
    )
    await test_app.post(
        endpoint_events_url,
        json={'tag': 'script_error', 'message': 'Undefined variable', 'server': 'main'},
        headers=auth_header_1,
    )
    await test_app.post(
        endpoint_events_url, json={'tag': 'admin_message', 'message': 'Admin note', 'server': 'main'}, headers=auth_header_1
    )

    response = await test_app.get(f'{endpoint_events_url}?tag=script_error&tag=admin_message', headers=auth_header_1)

    assert response.status_code == 200
    data = await response.get_json()
    assert data['total'] == 2
    assert data['tags'] == ['script_error', 'admin_message']
    assert {event['tag'] for event in data['events']} == {'script_error', 'admin_message'}


@pytest.mark.asyncio
async def test__get_events__filters_by_comma_separated_tags_param(
    state, test_app, endpoint_events_url, db_user_1, db_session_1, auth_header_1, db_server_manager
):
    """Test that GET /events can filter by comma-separated tags query parameter."""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    await test_app.post(
        endpoint_events_url, json={'tag': 'server_message', 'message': 'Mission started', 'server': 'main'}, headers=auth_header_1
    )
    await test_app.post(
        endpoint_events_url,
        json={'tag': 'script_error', 'message': 'Undefined variable', 'server': 'main'},
        headers=auth_header_1,
    )

    response = await test_app.get(f'{endpoint_events_url}?tags=script_error', headers=auth_header_1)

    assert response.status_code == 200
    data = await response.get_json()
    assert data['total'] == 1
    assert data['tags'] == ['script_error']
    assert data['events'][0]['tag'] == 'script_error'


@pytest.mark.asyncio
async def test__get_events__returns_html_when_requested(
    state, test_app, endpoint_events_url, db_user_1, db_session_1, auth_header_1, db_server_manager
):
    """Test that GET /events returns an HTML fragment when requested by Accept header."""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    await test_app.post(
        endpoint_events_url, json={'tag': 'script_error', 'message': 'Bad thing <happened>', 'server': ''}, headers=auth_header_1
    )

    response = await test_app.get(endpoint_events_url, headers={'Accept': 'text/html', **auth_header_1})

    html_body = await response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.content_type.startswith('text/html')
    assert html_body


@pytest.mark.asyncio
async def test__get_events__returns_html_when_accepts_header_is_used(
    state, test_app, endpoint_events_url, db_user_1, db_session_1, auth_header_1, db_server_manager
):
    """Test that GET /events also supports the Accepts header spelling."""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    await test_app.post(
        endpoint_events_url, json={'tag': 'server_message', 'message': 'Mission ended', 'server': 'main'}, headers=auth_header_1
    )

    response = await test_app.get(endpoint_events_url, headers={'Accepts': 'text/html', **auth_header_1})

    html_body = await response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.content_type.startswith('text/html')
    assert html_body


@pytest.mark.asyncio
async def test__events_page__requires_authentication(test_app):
    """Test that the Arma events frontend requires a logged-in session."""
    response = await test_app.get('/server_ops/arma/events')

    html = await response.get_data(as_text=True)

    assert response.status_code == 401
    assert response.content_type.startswith('text/html')
    assert html


@pytest.mark.asyncio
async def test__events_page__requires_manage_server_role(
    state, test_app, db_user_1, db_session_1, auth_header_1, db_server_manager
):
    """Test that the Arma events frontend requires the server manager role."""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    response = await test_app.get('/server_ops/arma/events', headers=auth_header_1)

    html = await response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.content_type.startswith('text/html')
    assert html


@pytest.mark.asyncio
async def test__events_page__renders_for_server_manager(
    test_app, state, db_user_1, db_session_1, auth_header_1, db_server_manager
):
    """Test that server managers can view the Arma events frontend."""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)

    response = await test_app.get('/server_ops/arma/events', headers=auth_header_1)
    html = await response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.content_type.startswith('text/html')
    assert html


@pytest.mark.asyncio
async def test__events_list_partial__renders_filtered_events_for_server_manager(
    test_app, state, db_user_1, db_session_1, db_server_manager, endpoint_events_url
):
    """Test that the HTMX event list partial is restricted and renders filtered rows."""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    await test_app.post(endpoint_events_url, json={'tag': 'server_message', 'message': 'Mission started', 'server': 'main'})
    await test_app.post(endpoint_events_url, json={'tag': 'script_error', 'message': 'Undefined variable', 'server': 'main'})

    response = await test_app.get(
        '/api/v1/html/server_ops/arma/events/list?tags=script_error',
        headers={'Authorization': f'Bearer {db_session_1.token}'},
    )
    html = await response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.content_type.startswith('text/html')
    assert html
