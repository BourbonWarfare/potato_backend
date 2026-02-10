# ruff: noqa: F811, F401

import pytest
from pathlib import Path

from integrations.fixtures import session, state
from integrations.server_ops.arma.fixtures import (
    workshop_details_1,
    workshop_details_2,
    workshop_details_3,
    mod_1,
    mod_2,
    mod_3,
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
    test_config_path,
    invalid_kind,
    duplicate_workshop_id,
)
from bw.server_ops.arma.api import ArmaApi
from bw.server_ops.arma.mod import MODS, MODLISTS, Mod, Modlist, Kind, WorkshopId
from bw.error import ServerConfigNotFound, ModAlreadyDefined, ModNotDefined, ModMissingField, ModInvalidKind


# Tests for get_all_configured_mods


def test__get_all_configured_mods__returns_all_mods(mocker, state, session, mock_mod_1, mock_mod_2):
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


def test__get_server_mods__returns_server_mods(mocker, state, session, server_name_1, mock_modlist_1):
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


def test__get_server_mods__raises_when_server_not_found(mocker, state, session, server_name_2):
    """Test that get_server_mods raises ServerConfigNotFound for nonexistent server"""
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {})

    response = ArmaApi().get_server_mods(server_name_2)

    assert response.status_code == 404


# Tests for get_all_configured_modlists


def test__get_all_configured_modlists__returns_all_modlists(mocker, state, session, mock_modlist_2, mock_modlist_3):
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


def test__get_server_modlist__returns_server_modlist(mocker, state, session, server_name_1, mock_modlist_1):
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


def test__get_server_modlist__raises_when_server_not_found(mocker, state, session, server_name_2):
    """Test that get_server_modlist raises ServerConfigNotFound for nonexistent server"""
    mocker.patch('bw.server_ops.arma.api.SERVER_MAP', {})

    response = ArmaApi().get_server_modlist(server_name_2)

    assert response.status_code == 404


# Tests for reload_mod_configuration


def test__reload_mod_configuration__calls_load_mods(mocker, state, session, test_config_path):
    """Test that reload_mod_configuration calls load_mods with correct path"""
    mock_load_mods = mocker.patch('bw.server_ops.arma.api.load_mods')

    response = ArmaApi().reload_mod_configuration(test_config_path)

    assert response.status_code == 200
    mock_load_mods.assert_called_once_with(test_config_path)


# Tests for reload_modlist_configuration


def test__reload_modlist_configuration__calls_load_modlists(mocker, state, session, test_config_path):
    """Test that reload_modlist_configuration calls load_modlists with correct path"""
    mock_load_modlists = mocker.patch('bw.server_ops.arma.api.load_modlists')

    response = ArmaApi().reload_modlist_configuration(test_config_path)

    assert response.status_code == 200
    mock_load_modlists.assert_called_once_with(test_config_path)


# Tests for flush_mods_to_disk


def test__flush_mods_to_disk__calls_save_mods(mocker, state, session, test_config_path):
    """Test that flush_mods_to_disk calls save_mods with correct path"""
    mock_save_mods = mocker.patch('bw.server_ops.arma.mod.save_mods')

    response = ArmaApi().flush_mods_to_disk(test_config_path)

    assert response.status_code == 200
    mock_save_mods.assert_called_once_with(test_config_path)


# Tests for flush_modlists_to_disk


def test__flush_modlists_to_disk__calls_save_modlists(mocker, state, session, test_config_path):
    """Test that flush_modlists_to_disk calls save_modlists with correct path"""
    mock_save_modlists = mocker.patch('bw.server_ops.arma.mod.save_modlists')

    response = ArmaApi().flush_modlists_to_disk(test_config_path)

    assert response.status_code == 200
    mock_save_modlists.assert_called_once_with(test_config_path)


# Tests for add_mod


def test__add_mod__successfully_adds_new_mod(mocker, state, session, mock_mod_name_3, mock_workshop_id_3):
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


def test__add_mod__raises_when_mod_already_exists(mocker, state, session, existing_mod_name, mock_workshop_id_1):
    """Test that add_mod raises ModAlreadyDefined when mod name already exists"""
    existing_mod = Mod(name=existing_mod_name, workshop_id=WorkshopId(mock_workshop_id_1))
    mocker.patch('bw.server_ops.arma.api.MODS', {existing_mod_name: existing_mod})

    response = ArmaApi().add_mod(
        mod_name=existing_mod_name, workshop_id=456789, kind='mod', manual_install=False, directory='@foobar'
    )

    assert response.status_code == 409


def test__add_mod__raises_when_workshop_id_missing_for_non_manual(mocker, state, session, mock_mod_name_3):
    """Test that add_mod raises ModMissingField when workshop_id missing for non-manual mod"""
    mocker.patch('bw.server_ops.arma.api.MODS', {})

    response = ArmaApi().add_mod(
        mod_name=mock_mod_name_3, workshop_id=None, kind='mod', manual_install=False, directory='@foobar'
    )

    assert response.status_code == 400


def test__add_mod__raises_when_mod_directory_missing_for_manual(mocker, state, session, mock_mod_name_3):
    """Test that add_mod raises ModMissingField when mod_directory missing for manual mod"""
    mocker.patch('bw.server_ops.arma.api.MODS', {})

    response = ArmaApi().add_mod(mod_name=mock_mod_name_3, workshop_id=None, kind='mod', manual_install=True, directory=None)

    assert response.status_code == 400


def test__add_mod__raises_when_invalid_kind(mocker, state, session, mock_mod_name_3, mock_workshop_id_3, invalid_kind):
    """Test that add_mod raises ModInvalidKind when kind is invalid"""
    mocker.patch('bw.server_ops.arma.api.MODS', {})

    response = ArmaApi().add_mod(
        mod_name=mock_mod_name_3, workshop_id=mock_workshop_id_3, kind=invalid_kind, manual_install=False, directory='@foobar'
    )

    assert response.status_code == 400


def test__add_mod__raises_when_duplicate_workshop_id(
    mocker, state, session, mock_mod_name_3, existing_mod_name, duplicate_workshop_id
):
    """Test that add_mod raises DuplicateModWorkshopID when workshop_id already exists"""
    existing_mod = Mod(name=existing_mod_name, workshop_id=WorkshopId(duplicate_workshop_id))
    mocker.patch('bw.server_ops.arma.api.MODS', {existing_mod_name: existing_mod})

    response = ArmaApi().add_mod(
        mod_name=mock_mod_name_3, workshop_id=duplicate_workshop_id, kind='mod', manual_install=False, directory='@foobar'
    )

    assert response.status_code == 400


def test__add_mod__adds_server_mod_with_required_directory(mocker, state, session, mock_mod_name_3, mock_workshop_id_3):
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


def test__add_mod__raises_when_directory_missing_for_server_mod(mocker, state, session, mock_mod_name_3, mock_workshop_id_3):
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


def test__add_modlist__successfully_adds_new_modlist(mocker, state, session, mock_mod_1, mock_mod_2, mock_modlist_name_4):
    """Test that add_modlist successfully adds a new modlist to MODLISTS dictionary"""
    mocker.patch('bw.server_ops.arma.api.MODS', {mock_mod_1.name: mock_mod_1, mock_mod_2.name: mock_mod_2})
    mocker.patch('bw.server_ops.arma.api.MODLISTS', {})

    response = ArmaApi().add_modlist(name=mock_modlist_name_4, mod_names=[mock_mod_1.name, mock_mod_2.name])

    assert response.status_code == 201
    from bw.server_ops.arma.api import MODLISTS

    assert mock_modlist_name_4 in MODLISTS


def test__add_modlist__raises_when_modlist_already_exists(
    mocker, state, session, mock_mod_1, mock_modlist_4, mock_modlist_name_5
):
    """Test that add_modlist raises ModAlreadyDefined when modlist name already exists"""
    mocker.patch('bw.server_ops.arma.api.MODS', {mock_mod_1.name: mock_mod_1})
    mocker.patch('bw.server_ops.arma.api.MODLISTS', {mock_modlist_name_5: mock_modlist_4})

    response = ArmaApi().add_modlist(name=mock_modlist_name_5, mod_names=[mock_mod_1.name])

    assert response.status_code == 409


def test__add_modlist__raises_when_mod_not_defined(mocker, state, session, nonexistent_mod_name, mock_modlist_name_4):
    """Test that add_modlist raises ModNotDefined when referenced mod doesn't exist"""
    mocker.patch('bw.server_ops.arma.api.MODS', {})
    mocker.patch('bw.server_ops.arma.api.MODLISTS', {})

    response = ArmaApi().add_modlist(name=mock_modlist_name_4, mod_names=[nonexistent_mod_name])

    assert response.status_code == 404


def test__add_modlist__creates_empty_modlist(mocker, state, session, mock_modlist_name_6):
    """Test that add_modlist can create a modlist with no mods"""
    mocker.patch('bw.server_ops.arma.api.MODS', {})
    mocker.patch('bw.server_ops.arma.api.MODLISTS', {})

    response = ArmaApi().add_modlist(name=mock_modlist_name_6, mod_names=[])

    assert response.status_code == 201
    from bw.server_ops.arma.api import MODLISTS

    assert mock_modlist_name_6 in MODLISTS
    assert len(MODLISTS[mock_modlist_name_6].mods) == 0


def test__add_modlist__validates_all_mods_before_adding(
    mocker, state, session, mock_mod_1, nonexistent_mod_name, mock_modlist_name_4
):
    """Test that add_modlist validates all mod names before adding the modlist"""
    mocker.patch('bw.server_ops.arma.api.MODS', {mock_mod_1.name: mock_mod_1})
    mocker.patch('bw.server_ops.arma.api.MODLISTS', {})

    # Should fail because nonexistent_mod doesn't exist
    response = ArmaApi().add_modlist(name=mock_modlist_name_4, mod_names=[mock_mod_1.name, nonexistent_mod_name])

    assert response.status_code == 404
    from bw.server_ops.arma.api import MODLISTS

    assert mock_modlist_name_4 not in MODLISTS
