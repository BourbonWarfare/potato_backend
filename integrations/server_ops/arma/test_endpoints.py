# ruff: noqa: F811, F401

import pytest

from integrations.fixtures import test_app, session, state
from integrations.auth.fixtures import (
    db_user_1,
    db_session_1,
    expire_invalid,
    db_expired_session_1,
    token_1,
    server_manager,
    server_manager_name,
    db_server_manager,
)
from integrations.server_ops.arma.fixtures import (
    mock_mod_1,
    mock_mod_2,
    mock_mod_name_1,
    mock_mod_name_2,
    mock_mod_name_3,
    mock_workshop_id_1,
    mock_workshop_id_2,
    mock_workshop_id_3,
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
    server_name_1,
    server_name_2,
    existing_mod_name,
    nonexistent_mod_name,
    endpoint_mods_url,
    endpoint_server_mods_url,
    endpoint_modlists_url,
    endpoint_server_modlist_url,
    endpoint_reload_mods_url,
    endpoint_reload_modlists_url,
    endpoint_arma_base_url,
)
from bw.server_ops.arma.mod import MODS, MODLISTS, Mod, Modlist, WorkshopId
from bw.auth.user import UserStore


# Tests for GET /mods


@pytest.mark.asyncio
async def test__get_configured_mods__returns_mods(mocker, state, session, test_app, endpoint_mods_url, mock_mod_1, mock_mod_2):
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
async def test__get_configured_mods__returns_empty_list(mocker, state, session, test_app, endpoint_mods_url):
    """Test that GET /mods returns empty list when no mods configured"""
    mocker.patch('bw.server_ops.arma.api.MODS', {})

    response = await test_app.get(endpoint_mods_url)

    assert response.status_code == 200
    data = await response.get_json()
    assert data['mods'] == []


# Tests for GET /mods/<server>


@pytest.mark.asyncio
async def test__get_server_mods__returns_server_mods(
    mocker, state, session, test_app, endpoint_server_mods_url, server_name_1, mock_modlist_1
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
    mocker, state, session, test_app, endpoint_arma_base_url, server_name_2
):
    """Test that GET /mods/<server> returns 404 for nonexistent server"""
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {})

    response = await test_app.get(f'{endpoint_arma_base_url}/mods/{server_name_2}')

    assert response.status_code == 404


# Tests for GET /mods/lists


@pytest.mark.asyncio
async def test__get_configured_modlists__returns_modlists(
    mocker, state, session, test_app, endpoint_modlists_url, mock_modlist_2, mock_modlist_3
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
async def test__get_configured_modlists__returns_empty_dict(mocker, state, session, test_app, endpoint_modlists_url):
    """Test that GET /mods/lists returns empty dict when no modlists configured"""
    mocker.patch('bw.server_ops.arma.api.MODLISTS', {})

    response = await test_app.get(endpoint_modlists_url)

    assert response.status_code == 200
    data = await response.get_json()
    assert data['modlists'] == {}


# Tests for GET /mods/list/<server>


@pytest.mark.asyncio
async def test__get_server_modlist__returns_server_modlist(
    mocker, state, session, test_app, endpoint_server_modlist_url, server_name_1, mock_modlist_1
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
    mocker, state, session, test_app, endpoint_arma_base_url, server_name_2
):
    """Test that GET /mods/list/<server> returns 404 for nonexistent server"""
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {})

    response = await test_app.get(f'{endpoint_arma_base_url}/mods/list/{server_name_2}')

    assert response.status_code == 404


# Tests for POST /mods/reload


@pytest.mark.asyncio
async def test__reload_mods__reloads_successfully(
    mocker, state, session, test_app, db_user_1, db_session_1, db_server_manager, endpoint_reload_mods_url
):
    """Test that POST /mods/reload reloads mod configuration"""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    mock_load_mods = mocker.patch('bw.server_ops.arma.api.load_mods')
    mocker.patch('bw.server_ops.arma.endpoints.ENVIRONMENT.arma_mod_config_path', '/test/path')

    response = await test_app.post(endpoint_reload_mods_url, headers={'Authorization': f'Bearer {db_session_1.token}'})

    assert response.status_code == 200
    mock_load_mods.assert_called_once()


@pytest.mark.asyncio
async def test__reload_mods__requires_authentication(state, session, test_app, endpoint_reload_mods_url):
    """Test that POST /mods/reload requires authentication"""
    response = await test_app.post(endpoint_reload_mods_url)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test__reload_mods__requires_permission(state, session, test_app, db_user_1, db_session_1, endpoint_reload_mods_url):
    """Test that POST /mods/reload requires can_manage_server role"""
    response = await test_app.post(endpoint_reload_mods_url, headers={'Authorization': f'Bearer {db_session_1.token}'})

    assert response.status_code == 403


@pytest.mark.asyncio
async def test__reload_mods__rejects_expired_session(
    mocker, state, session, test_app, db_user_1, db_expired_session_1, db_server_manager, endpoint_reload_mods_url
):
    """Test that POST /mods/reload rejects expired sessions"""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)

    response = await test_app.post(endpoint_reload_mods_url, headers={'Authorization': f'Bearer {db_expired_session_1.token}'})

    assert response.status_code == 401


# Tests for POST /mods/lists/reload


@pytest.mark.asyncio
async def test__reload_modlists__reloads_successfully(
    mocker, state, session, test_app, db_user_1, db_session_1, db_server_manager, endpoint_reload_modlists_url
):
    """Test that POST /mods/lists/reload reloads modlist configuration"""
    UserStore().assign_user_role(state, db_user_1, db_server_manager.name)
    mock_load_modlists = mocker.patch('bw.server_ops.arma.api.load_modlists')
    mocker.patch('bw.server_ops.arma.endpoints.ENVIRONMENT.arma_modlist_config_path', '/test/path')

    response = await test_app.post(endpoint_reload_modlists_url, headers={'Authorization': f'Bearer {db_session_1.token}'})

    assert response.status_code == 200
    mock_load_modlists.assert_called_once()


@pytest.mark.asyncio
async def test__reload_modlists__requires_authentication(state, session, test_app, endpoint_reload_modlists_url):
    """Test that POST /mods/lists/reload requires authentication"""
    response = await test_app.post(endpoint_reload_modlists_url)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test__reload_modlists__requires_permission(
    state, session, test_app, db_user_1, db_session_1, endpoint_reload_modlists_url
):
    """Test that POST /mods/lists/reload requires can_manage_server role"""
    response = await test_app.post(endpoint_reload_modlists_url, headers={'Authorization': f'Bearer {db_session_1.token}'})

    assert response.status_code == 403


# Tests for POST /mods


@pytest.mark.asyncio
async def test__add_new_mod__creates_mod_successfully(
    mocker,
    state,
    session,
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
async def test__add_new_mod__requires_authentication(
    state, session, test_app, endpoint_mods_url, mock_mod_name_3, mock_workshop_id_3
):
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
    state, session, test_app, db_user_1, db_session_1, endpoint_mods_url, mock_mod_name_3, mock_workshop_id_3
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
    session,
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
    session,
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
    mocker, state, session, test_app, db_user_1, db_session_1, db_server_manager, endpoint_mods_url, mock_mod_name_3
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
    session,
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
    state, session, test_app, endpoint_modlists_url, mock_mod_name_1, mock_mod_name_2, mock_modlist_name_4
):
    """Test that POST /mods/lists requires authentication"""
    response = await test_app.post(
        endpoint_modlists_url, json={'name': mock_modlist_name_4, 'mods': [mock_mod_name_1, mock_mod_name_2]}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test__add_new_modlist__requires_permission(
    state,
    session,
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
    session,
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
    session,
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
    mocker, state, session, test_app, db_user_1, db_session_1, db_server_manager, endpoint_modlists_url, mock_modlist_name_6
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
