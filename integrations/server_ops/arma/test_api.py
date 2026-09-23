# ruff: noqa: F811, F401

import os
from pathlib import Path

import pytest

from bw.error import (
    ArmaServerUnresponsive,
    ModAlreadyDefined,
    ModInvalidKind,
    ModMissingField,
    ModNotDefined,
    ServerConfigNotFound,
    SubprocessFailed,
)
from bw.server_ops.arma.api import ArmaApi
from bw.server_ops.arma.mod import MODLISTS, MODS, Kind, Mod, Modlist, WorkshopId
from integrations.server_ops.arma.fixtures import (
    duplicate_workshop_id,
    existing_mod_name,
    invalid_kind,
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
    mod_1,
    mod_2,
    mod_3,
    nonexistent_mod_name,
    server_name_1,
    server_name_2,
    server_name_3,
    server_name_4,
    test_config_path,
    workshop_details_1,
    workshop_details_2,
    workshop_details_3,
)

# Tests for get_latest_rpt


@pytest.mark.asyncio
async def test__get_latest_rpt__returns_latest_rpt_content(mocker, state, server_name_1, tmp_path):
    """Test that get_latest_rpt returns the content of the newest RPT file for the server"""
    # Arrange: Set up mock files with distinct modification times
    old_file = tmp_path / 'old_log.rpt'
    new_file = tmp_path / 'new_log.rpt'
    ignored_file = tmp_path / 'other_file.txt'

    old_file.write_text('older rpt log content')
    new_file.write_text('newest rpt log content')
    ignored_file.write_text('ignore this content')

    # Explicitly set modification times (new_file is newer)
    os.utime(old_file, (1000, 1000))
    os.utime(new_file, (2000, 2000))

    mock_server = mocker.Mock()
    mock_server.server_rpt.return_value = tmp_path

    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {server_name_1: mock_server})

    # Act
    response = ArmaApi().get_latest_rpt(server_name_1)

    # Assert: Verify observed contract/behavior
    assert response.status_code == 200
    assert response.headers.get('Transfer-Encoding') == 'chunked'
    assert await response.get_data(as_text=True) == 'newest rpt log content'


def test__get_latest_rpt__raises_when_server_not_found(mocker, state, server_name_2):
    """Test that get_latest_rpt returns 404 when the requested server does not exist"""
    # Arrange
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {})

    # Act
    response = ArmaApi().get_latest_rpt(server_name_2)

    # Assert
    assert response.status_code == 404


def test__get_latest_rpt__raises_when_no_rpt_files_exist(mocker, state, server_name_1, tmp_path):
    """Test that get_latest_rpt returns 404 when the directory contains no .rpt files"""
    # Arrange: Directory exists, but has no files matching *.rpt
    (tmp_path / 'readme.txt').write_text('just a text file')

    mock_server = mocker.Mock()
    mock_server.server_rpt.return_value = tmp_path

    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {server_name_1: mock_server})

    # Act
    response = ArmaApi().get_latest_rpt(server_name_1)

    # Assert
    assert response.status_code == 404


# Tests for get_all_configured_mods


def test__get_all_configured_mods__returns_all_mods(mocker, state, mock_mod_1, mock_mod_2):
    """Test that get_all_configured_mods returns all configured mods"""
    mock_mods = {
        mock_mod_1.name: mock_mod_1,
        mock_mod_2.name: mock_mod_2,
    }
    mocker.patch('bw.server_ops.arma.api.MODS', mock_mods)

    response = ArmaApi().get_all_configured_mods()

    assert response.status_code == 200
    assert 'mods' in response.contained_json
    assert len(response.contained_json['mods']) == 2
    assert mock_mod_1.name in [mod['name'] for mod in response.contained_json['mods']]
    assert mock_mod_2.name in [mod['name'] for mod in response.contained_json['mods']]


def test__get_all_configured_mods__returns_empty_when_no_mods(mocker, state, session):
    """Test that get_all_configured_mods returns empty list when no mods configured"""
    mocker.patch('bw.server_ops.arma.api.MODS', {})

    response = ArmaApi().get_all_configured_mods()

    assert response.status_code == 200
    assert response.contained_json['mods'] == []


# Tests for get_server_mods


def test__get_server_mods__returns_server_mods(mocker, state, server_name_1, mock_modlist_1):
    """Test that get_server_mods returns mods for a specific server"""
    mock_server = mocker.Mock()
    mock_server.modlist.return_value = mock_modlist_1

    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {server_name_1: mock_server})

    response = ArmaApi().get_server_mods(server_name_1)

    assert response.status_code == 200
    assert 'mods' in response.contained_json
    assert len(response.contained_json['mods']) == 2
    assert mock_modlist_1.mods[0].name in [mod['name'] for mod in response.contained_json['mods']]
    assert mock_modlist_1.mods[1].name in [mod['name'] for mod in response.contained_json['mods']]


def test__get_server_mods__raises_when_server_not_found(mocker, state, server_name_2):
    """Test that get_server_mods raises ServerConfigNotFound for nonexistent server"""
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {})

    response = ArmaApi().get_server_mods(server_name_2)

    assert response.status_code == 404


# Tests for get_all_configured_modlists


def test__get_all_configured_modlists__returns_all_modlists(mocker, state, mock_modlist_2, mock_modlist_3):
    """Test that get_all_configured_modlists returns all configured modlists"""
    mock_modlists = {
        mock_modlist_2.name: mock_modlist_2,
        mock_modlist_3.name: mock_modlist_3,
    }
    mocker.patch('bw.server_ops.arma.api.MODLISTS', mock_modlists)

    response = ArmaApi().get_all_configured_modlists()

    assert response.status_code == 200
    assert 'modlists' in response.contained_json
    assert len(response.contained_json['modlists']) == 2
    assert mock_modlist_2.name in response.contained_json['modlists']
    assert mock_modlist_3.name in response.contained_json['modlists']


def test__get_all_configured_modlists__returns_empty_when_no_modlists(mocker, state, session):
    """Test that get_all_configured_modlists returns empty dict when no modlists configured"""
    mocker.patch('bw.server_ops.arma.api.MODLISTS', {})

    response = ArmaApi().get_all_configured_modlists()

    assert response.status_code == 200
    assert response.contained_json['modlists'] == {}


# Tests for get_server_modlist


def test__get_server_modlist__returns_server_modlist(mocker, state, server_name_1, mock_modlist_1):
    """Test that get_server_modlist returns modlist for a specific server"""
    mock_server = mocker.Mock()
    mock_server.modlist.return_value = mock_modlist_1
    mock_server._config.require.return_value.get.return_value = mock_modlist_1.name

    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {server_name_1: mock_server})

    response = ArmaApi().get_server_modlist(server_name_1)

    assert response.status_code == 200
    assert response.contained_json['modlist_name'] == mock_modlist_1.name
    assert len(response.contained_json['mods']) == 2
    assert mock_modlist_1.mods[0].name in response.contained_json['mods']
    assert mock_modlist_1.mods[1].name in response.contained_json['mods']


def test__get_server_modlist__raises_when_server_not_found(mocker, state, server_name_2):
    """Test that get_server_modlist raises ServerConfigNotFound for nonexistent server"""
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {})

    response = ArmaApi().get_server_modlist(server_name_2)

    assert response.status_code == 404


# Tests for add_mod


def test__add_mod__successfully_adds_new_mod(mocker, state, mock_mod_name_3, mock_workshop_id_3):
    """Test that add_mod successfully adds a new mod to MODS dictionary"""
    mocker.patch('bw.server_ops.arma.api.MODS', {})

    response = ArmaApi().add_mod(
        mod_name=mock_mod_name_3,
        workshop_id=mock_workshop_id_3,
        kind='mod',
        manual_install=False,
        directory='@foobar',
    )

    assert response.status_code == 201
    from bw.server_ops.arma.api import MODS

    assert mock_mod_name_3 in MODS


def test__add_mod__raises_when_mod_already_exists(mocker, state, existing_mod_name, mock_workshop_id_1):
    """Test that add_mod raises ModAlreadyDefined when mod name already exists"""
    existing_mod = Mod(name=existing_mod_name, workshop_id=WorkshopId(mock_workshop_id_1))
    mocker.patch('bw.server_ops.arma.api.MODS', {existing_mod_name: existing_mod})

    response = ArmaApi().add_mod(
        mod_name=existing_mod_name, workshop_id=456789, kind='mod', manual_install=False, directory='@foobar'
    )

    assert response.status_code == 409


def test__add_mod__raises_when_workshop_id_missing_for_non_manual(mocker, state, mock_mod_name_3):
    """Test that add_mod raises ModMissingField when workshop_id missing for non-manual mod"""
    mocker.patch('bw.server_ops.arma.api.MODS', {})

    response = ArmaApi().add_mod(
        mod_name=mock_mod_name_3, workshop_id=None, kind='mod', manual_install=False, directory='@foobar'
    )

    assert response.status_code == 400


def test__add_mod__raises_when_mod_directory_missing_for_manual(mocker, state, mock_mod_name_3):
    """Test that add_mod raises ModMissingField when mod_directory missing for manual mod"""
    mocker.patch('bw.server_ops.arma.api.MODS', {})

    response = ArmaApi().add_mod(mod_name=mock_mod_name_3, workshop_id=None, kind='mod', manual_install=True, directory=None)

    assert response.status_code == 400


def test__add_mod__raises_when_invalid_kind(mocker, state, mock_mod_name_3, mock_workshop_id_3, invalid_kind):
    """Test that add_mod raises ModInvalidKind when kind is invalid"""
    mocker.patch('bw.server_ops.arma.api.MODS', {})

    response = ArmaApi().add_mod(
        mod_name=mock_mod_name_3, workshop_id=mock_workshop_id_3, kind=invalid_kind, manual_install=False, directory='@foobar'
    )

    assert response.status_code == 400


def test__add_mod__raises_when_duplicate_workshop_id(mocker, state, mock_mod_name_3, existing_mod_name, duplicate_workshop_id):
    """Test that add_mod raises DuplicateModWorkshopID when workshop_id already exists"""
    existing_mod = Mod(name=existing_mod_name, workshop_id=WorkshopId(duplicate_workshop_id))
    mocker.patch('bw.server_ops.arma.api.MODS', {existing_mod_name: existing_mod})

    response = ArmaApi().add_mod(
        mod_name=mock_mod_name_3, workshop_id=duplicate_workshop_id, kind='mod', manual_install=False, directory='@foobar'
    )

    assert response.status_code == 400


def test__add_mod__adds_server_mod_with_required_directory(mocker, state, mock_mod_name_3, mock_workshop_id_3):
    """Test that add_mod successfully adds server_mod with directory"""
    mocker.patch('bw.server_ops.arma.api.MODS', {})

    response = ArmaApi().add_mod(
        mod_name=mock_mod_name_3,
        workshop_id=mock_workshop_id_3,
        kind='server_mod',
        manual_install=False,
        directory='@new_server_mod',
    )

    assert response.status_code == 201


def test__add_mod__raises_when_directory_missing_for_server_mod(mocker, state, mock_mod_name_3, mock_workshop_id_3):
    """Test that add_mod raises ModMissingField when directory missing for server_mod"""
    mocker.patch('bw.server_ops.arma.api.MODS', {})

    response = ArmaApi().add_mod(
        mod_name=mock_mod_name_3,
        workshop_id=mock_workshop_id_3,
        kind='server_mod',
        manual_install=False,
        directory=None,
    )

    assert response.status_code == 400


# Tests for add_modlist


def test__add_modlist__successfully_adds_new_modlist(mocker, state, mock_mod_1, mock_mod_2, mock_modlist_name_4):
    """Test that add_modlist successfully adds a new modlist to MODLISTS dictionary"""
    mocker.patch('bw.server_ops.arma.api.MODS', {mock_mod_1.name: mock_mod_1, mock_mod_2.name: mock_mod_2})
    mocker.patch('bw.server_ops.arma.api.MODLISTS', {})

    response = ArmaApi().add_modlist(name=mock_modlist_name_4, mod_names=[mock_mod_1.name, mock_mod_2.name])

    assert response.status_code == 201
    from bw.server_ops.arma.api import MODLISTS

    assert mock_modlist_name_4 in MODLISTS


def test__add_modlist__raises_when_modlist_already_exists(mocker, state, mock_mod_1, mock_modlist_4, mock_modlist_name_5):
    """Test that add_modlist raises ModAlreadyDefined when modlist name already exists"""
    mocker.patch('bw.server_ops.arma.api.MODS', {mock_mod_1.name: mock_mod_1})
    mocker.patch('bw.server_ops.arma.api.MODLISTS', {mock_modlist_name_5: mock_modlist_4})

    response = ArmaApi().add_modlist(name=mock_modlist_name_5, mod_names=[mock_mod_1.name])

    assert response.status_code == 409


def test__add_modlist__raises_when_mod_not_defined(mocker, state, nonexistent_mod_name, mock_modlist_name_4):
    """Test that add_modlist raises ModNotDefined when referenced mod doesn't exist"""
    mocker.patch('bw.server_ops.arma.api.MODS', {})
    mocker.patch('bw.server_ops.arma.api.MODLISTS', {})

    response = ArmaApi().add_modlist(name=mock_modlist_name_4, mod_names=[nonexistent_mod_name])

    assert response.status_code == 404


def test__add_modlist__creates_empty_modlist(mocker, state, mock_modlist_name_6):
    """Test that add_modlist can create a modlist with no mods"""
    mocker.patch('bw.server_ops.arma.api.MODS', {})
    mocker.patch('bw.server_ops.arma.api.MODLISTS', {})

    response = ArmaApi().add_modlist(name=mock_modlist_name_6, mod_names=[])

    assert response.status_code == 201
    from bw.server_ops.arma.api import MODLISTS

    assert mock_modlist_name_6 in MODLISTS
    assert len(MODLISTS[mock_modlist_name_6].mods) == 0


def test__add_modlist__validates_all_mods_before_adding(mocker, state, mock_mod_1, nonexistent_mod_name, mock_modlist_name_4):
    """Test that add_modlist validates all mod names before adding the modlist"""
    mocker.patch('bw.server_ops.arma.api.MODS', {mock_mod_1.name: mock_mod_1})
    mocker.patch('bw.server_ops.arma.api.MODLISTS', {})

    # Should fail because nonexistent_mod doesn't exist
    response = ArmaApi().add_modlist(name=mock_modlist_name_4, mod_names=[mock_mod_1.name, nonexistent_mod_name])

    assert response.status_code == 404
    from bw.server_ops.arma.api import MODLISTS

    assert mock_modlist_name_4 not in MODLISTS


def test__get_all_servers__returns_all_servers(
    mocker, state, server_name_1, server_name_2, server_name_3, mock_server_1, mock_server_2, mock_server_3
):
    """Test that get_all_servers returns all configured servers"""
    mock_server_map = {
        server_name_1: mock_server_1,
        server_name_2: mock_server_2,
        server_name_3: mock_server_3,
    }
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', mock_server_map)

    response = ArmaApi().get_all_servers()

    assert response.status_code == 200
    assert 'servers' in response.contained_json
    assert len(response.contained_json['servers']) == 3
    assert server_name_1 == response.contained_json['servers'][0]
    assert server_name_2 == response.contained_json['servers'][2]
    assert server_name_3 == response.contained_json['servers'][1]


def test__get_all_servers__returns_empty_when_no_servers(mocker, state, session):
    """Test that get_all_servers returns empty list when no servers configured"""
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {})

    response = ArmaApi().get_all_servers()

    assert response.status_code == 200
    assert response.contained_json['servers'] == []


# Additional server operation coverage


def test__get_server_from_string__returns_configured_server(mocker, server_name_1, mock_server_1):
    """Test that get_server_from_string returns the configured server object."""
    # Not yet reviewed
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {server_name_1: mock_server_1})

    server = ArmaApi().get_server_from_string(server_name_1)

    assert server is mock_server_1


def test__get_server_from_string__raises_when_server_missing(mocker, server_name_2):
    """Test that get_server_from_string raises when the server is not configured."""
    # Not yet reviewed
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {})

    with pytest.raises(ServerConfigNotFound):
        ArmaApi().get_server_from_string(server_name_2)


def test__reload_server_configs__loads_configs_and_publishes_event(mocker, tmp_path):
    """Test that reload_server_configs reloads from disk and publishes an event."""
    # Not yet reviewed
    load_server_config_directory = mocker.patch('bw.server_ops.arma.api.load_server_config_directory')
    publish = mocker.patch('bw.server_ops.arma.api.State.broker.publish')

    response = ArmaApi().reload_server_configs(tmp_path)

    assert response.status_code == 200
    load_server_config_directory.assert_called_once_with(tmp_path)
    publish.assert_called_once()


@pytest.mark.asyncio
async def test__server_ping__returns_ping_value(mocker):
    """Test that server_ping returns the subprocess ping value."""
    # Not yet reviewed
    mocker.patch('bw.server_ops.arma.api.a3sb.ping.acall', return_value=(12.5, ''))

    response = await ArmaApi().server_ping('localhost', 2303)

    assert response.status_code == 200
    assert await response.get_data(as_text=True) == '12.5'


@pytest.mark.asyncio
async def test__server_ping__returns_error_when_server_unresponsive(mocker):
    """Test that server_ping maps unresponsive server errors through the API wrapper."""
    # Not yet reviewed
    mocker.patch('bw.server_ops.arma.api.a3sb.ping.acall', side_effect=ArmaServerUnresponsive())

    response = await ArmaApi().server_ping('localhost', 2303)

    assert response.status_code == 504


@pytest.mark.asyncio
async def test__server_steam_status__returns_success_payload(mocker):
    """Test that server_steam_status returns server status fields when the query succeeds."""
    # Not yet reviewed
    query = {
        'name': 'server',
        'game': 'mission',
        'keywords': {'server_state': 'PLAYING'},
        'map': 'Altis',
        'players': 12,
        'max_players': 64,
    }
    mocker.patch('bw.server_ops.arma.api.a3sb.info.acall', return_value=(__import__('json').dumps(query), ''))

    response = await ArmaApi().server_steam_status('localhost', 2303)

    assert response.status_code == 200
    assert response.contained_json['result'] == 'success'
    assert response.contained_json['name'] == 'server'
    assert response.contained_json['mission'] == 'mission'
    assert response.contained_json['state'] == 'PLAYING'
    assert response.contained_json['map'] == 'Altis'
    assert response.contained_json['players'] == 12
    assert response.contained_json['max_players'] == 64


@pytest.mark.asyncio
async def test__server_steam_status__returns_failure_payload_on_subprocess_failure(mocker):
    """Test that server_steam_status returns a failure payload when the subprocess fails."""
    # Not yet reviewed
    mocker.patch(
        'bw.server_ops.arma.api.a3sb.info.acall',
        side_effect=SubprocessFailed('a3sb', 'failed', 'stdout', 'stderr'),
    )

    response = await ArmaApi().server_steam_status('localhost', 2303)

    assert response.status_code == 200
    assert response.contained_json == {'result': 'failure', 'reason': 'failed'}


@pytest.mark.asyncio
async def test__server_steam_status__returns_unresponsive_payload(mocker):
    """Test that server_steam_status returns an unresponsive payload when the server does not answer."""
    # Not yet reviewed
    mocker.patch('bw.server_ops.arma.api.a3sb.info.acall', side_effect=ArmaServerUnresponsive())

    response = await ArmaApi().server_steam_status('localhost', 2303)

    assert response.status_code == 200
    assert response.contained_json['result'] == 'unresponsive'


@pytest.mark.asyncio
async def test__start_server__reloads_config_and_delegates_to_process_api(mocker, state, server_name_1, mock_server_1):
    """Test that start_server reloads config and delegates to Arma3Api."""
    # Not yet reviewed
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {server_name_1: mock_server_1})
    start_server = mocker.patch('bw.server_ops.arma.api.Arma3Api.start_server', return_value={'running': True})

    response = await ArmaApi().start_server(state, server_name_1)

    assert response.contained_json == {'running': True}
    mock_server_1.reload_config.assert_called_once_with()
    start_server.assert_called_once_with(state, mock_server_1)


@pytest.mark.asyncio
async def test__stop_server__delegates_to_process_api(mocker, state, server_name_1, mock_server_1):
    """Test that stop_server delegates to Arma3Api."""
    # Not yet reviewed
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {server_name_1: mock_server_1})
    stop_server = mocker.patch('bw.server_ops.arma.api.Arma3Api.stop_server', return_value={'running': False})

    response = await ArmaApi().stop_server(state, server_name_1)

    assert response.contained_json == {'running': False}
    stop_server.assert_called_once_with(state, mock_server_1)


def test__flush_mods_to_disk__saves_mod_config(mocker, tmp_path):
    """Test that flush_mods_to_disk delegates to save_mod_configs."""
    # Not yet reviewed
    save_mod_configs = mocker.patch('bw.server_ops.arma.api.save_mod_configs')

    response = ArmaApi().flush_mods_to_disk(tmp_path)

    assert response.status_code == 200
    save_mod_configs.assert_called_once_with(tmp_path)


def test__flush_modlists_to_disk__saves_modlist_config(mocker, tmp_path):
    """Test that flush_modlists_to_disk delegates to save_modlists."""
    # Not yet reviewed
    save_modlists = mocker.patch('bw.server_ops.arma.mod.save_modlists')

    response = ArmaApi().flush_modlists_to_disk(tmp_path)

    assert response.status_code == 200
    save_modlists.assert_called_once_with(tmp_path)


def test__deploy_mods__creates_links_and_publishes_event(mocker, tmp_path, server_name_1):
    """Test that deploy_mods creates mod links and publishes a deployment event."""
    # Not yet reviewed
    mod_install_path = tmp_path / 'server_mods'
    mod_source = tmp_path / 'mods' / '@example'
    mod_source.mkdir(parents=True)
    mod = Mod(directory=tmp_path / 'mods', name='Example', filename='example', manual_install=True)
    modlist = Modlist('main', mods=[mod])
    server = mocker.Mock()
    server.mod_install_path.return_value = mod_install_path
    server.modlist.return_value = modlist
    server.server_name.return_value = server_name_1
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {server_name_1: server})
    symlink = mocker.patch('bw.server_ops.arma.api.os.symlink')
    publish = mocker.patch('bw.server_ops.arma.api.State.broker.publish')

    response = ArmaApi().deploy_mods(server_name_1)

    assert response.status_code == 200
    assert mod_install_path.exists()
    symlink.assert_called_once_with(mod_source, mod_install_path / '@example', target_is_directory=True)
    publish.assert_called_once()
    assert publish.call_args.args[0].server == server_name_1
    assert publish.call_args.args[0].mods == ['Example']


def test__deploy_mods__continues_when_symlink_fails(mocker, tmp_path, server_name_1):
    """Test that deploy_mods continues when creating a symlink fails."""
    # Not yet reviewed
    mod = Mod(directory=tmp_path / 'mods', name='Example', filename='example', manual_install=True)
    modlist = Modlist('main', mods=[mod])
    server = mocker.Mock()
    server.mod_install_path.return_value = tmp_path / 'server_mods'
    server.modlist.return_value = modlist
    server.server_name.return_value = server_name_1
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {server_name_1: server})
    mocker.patch('bw.server_ops.arma.api.os.symlink', side_effect=OSError('no link'))

    response = ArmaApi().deploy_mods(server_name_1)

    assert response.status_code == 200


def test__deploy_keys__copies_keys_and_publishes_event(mocker, tmp_path, server_name_1):
    """Test that deploy_keys copies bikeys and publishes a deployment event."""
    # Not yet reviewed
    mod = Mod(directory=tmp_path / 'mods', name='Example', filename='example', manual_install=True)
    key_source_path = mod.download_path() / 'keys'
    key_source_path.mkdir(parents=True)
    key_source = key_source_path / 'example.bikey'
    key_source.write_text('key-data')
    key_install_path = tmp_path / 'server_keys'
    modlist = Modlist('main', mods=[mod])
    server = mocker.Mock()
    server.key_install_path.return_value = key_install_path
    server.modlist.return_value = modlist
    server.server_name.return_value = server_name_1
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {server_name_1: server})
    publish = mocker.patch('bw.server_ops.arma.api.State.broker.publish')

    response = ArmaApi().deploy_keys(server_name_1)

    assert response.status_code == 200
    assert (key_install_path / 'example.bikey').read_text() == 'key-data'
    publish.assert_called_once()
    assert publish.call_args.args[0].server == server_name_1


def test__deploy_keys__skips_existing_identical_key(mocker, tmp_path, server_name_1):
    """Test that deploy_keys skips an existing key with identical contents."""
    # Not yet reviewed
    mod = Mod(directory=tmp_path / 'mods', name='Example', filename='example', manual_install=True)
    key_source_path = mod.download_path() / 'keys'
    key_source_path.mkdir(parents=True)
    (key_source_path / 'example.bikey').write_text('key-data')
    key_install_path = tmp_path / 'server_keys'
    key_install_path.mkdir()
    (key_install_path / 'example.bikey').write_text('key-data')
    modlist = Modlist('main', mods=[mod])
    server = mocker.Mock()
    server.key_install_path.return_value = key_install_path
    server.modlist.return_value = modlist
    server.server_name.return_value = server_name_1
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {server_name_1: server})
    copy = mocker.patch('bw.server_ops.arma.api.shutil.copy')

    response = ArmaApi().deploy_keys(server_name_1)

    assert response.status_code == 200
    copy.assert_not_called()
