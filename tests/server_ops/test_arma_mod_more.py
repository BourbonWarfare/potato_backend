import datetime

import pytest

from bw.error import ModNotDefined
from bw.server_ops.arma.mod import MODLISTS, MODS, Kind, Mod, Modlist, SteamWorkshopDetails, WorkshopId
from bw.settings import TIMEZONE


@pytest.fixture(autouse=True)
def clear_mod_globals():
    MODS.clear()
    MODLISTS.clear()
    yield
    MODS.clear()
    MODLISTS.clear()


@pytest.fixture(scope='session')
def workshop_id_1():
    return WorkshopId(123456)


@pytest.fixture(scope='session')
def workshop_update_date_1():
    return datetime.datetime(2024, 1, 2, 3, 4, 5, tzinfo=TIMEZONE)


@pytest.fixture(scope='session')
def workshop_details_1(workshop_id_1, workshop_update_date_1):
    return SteamWorkshopDetails(
        workshop_id=workshop_id_1,
        title='Example Mod',
        file_size_bytes=1234,
        last_update=workshop_update_date_1,
        preview_url='https://example.invalid/image.png',
    )


@pytest.fixture(scope='session')
def workshop_details_json_1(workshop_id_1, workshop_update_date_1):
    return {
        'workshop_id': str(workshop_id_1),
        'title': 'Example Mod',
        'file_size_bytes': 1234,
        'last_update': workshop_update_date_1.isoformat(),
        'preview_url': 'https://example.invalid/image.png',
    }


@pytest.fixture(scope='session')
def steam_json_1(workshop_id_1):
    return {
        'publishedfileid': str(workshop_id_1),
        'title': 'Example Mod',
        'file_size': 1234,
        'time_updated': 1700000000,
        'preview_url': 'https://example.invalid/image.png',
    }


@pytest.fixture(scope='session')
def mod_directory_1(tmp_path_factory):
    return tmp_path_factory.mktemp('mods')


@pytest.fixture(scope='session')
def mod_1(mod_directory_1, workshop_id_1):
    return Mod(
        directory=mod_directory_1,
        config_name='example_mod',
        name='Example Mod',
        filename='example',
        workshop_id=workshop_id_1,
        manual_install=False,
        kind=Kind.MOD,
    )


@pytest.fixture(scope='session')
def manual_mod_1(mod_directory_1):
    return Mod(
        directory=mod_directory_1,
        config_name='manual_mod',
        name='Manual Mod',
        filename='manual',
        workshop_id=None,
        manual_install=True,
        kind=Kind.MOD,
    )


@pytest.fixture(scope='session')
def modlist_name_1():
    return 'main'


def test__steam_workshop_details__to_json_serializes_machine_fields(workshop_details_1, workshop_details_json_1):
    """Test that SteamWorkshopDetails serializes its machine-readable fields."""
    # Not yet reviewed
    assert workshop_details_1.to_json() == workshop_details_json_1


def test__steam_workshop_details__from_json_round_trips(workshop_details_1, workshop_details_json_1):
    """Test that SteamWorkshopDetails can be reconstructed from JSON."""
    # Not yet reviewed
    assert SteamWorkshopDetails.from_json(workshop_details_json_1) == workshop_details_1


def test__steam_workshop_details__from_json_uses_defaults_for_missing_fields():
    """Test that SteamWorkshopDetails uses defaults for missing JSON fields."""
    # Not yet reviewed
    details = SteamWorkshopDetails.from_json({})

    assert details.workshop_id == WorkshopId(-1)
    assert details.title == 'Unknown'
    assert details.file_size_bytes == 0
    assert details.preview_url == ''


def test__steam_workshop_details__from_steam_json_maps_steam_fields(steam_json_1, workshop_id_1):
    """Test that SteamWorkshopDetails maps Steam API field names."""
    # Not yet reviewed
    details = SteamWorkshopDetails.from_steam_json(steam_json_1)

    assert details.workshop_id == workshop_id_1
    assert details.title == steam_json_1['title']
    assert details.file_size_bytes == steam_json_1['file_size']
    assert details.preview_url == steam_json_1['preview_url']


def test__mod__to_json_serializes_machine_fields(mod_1, workshop_id_1):
    """Test that Mod serializes its machine-readable fields."""
    # Not yet reviewed
    assert mod_1.to_json() == {
        'name': 'Example Mod',
        'config_name': 'example_mod',
        'filename': 'example',
        'workshop_id': str(workshop_id_1),
        'manual_install': False,
        'kind': Kind.MOD,
    }


def test__mod__as_launch_parameter_returns_arma_argument(mod_1):
    """Test that Mod.as_launch_parameter returns the Arma launch argument."""
    # Not yet reviewed
    assert mod_1.as_launch_parameter() == '@example'


def test__mod__download_path_uses_workshop_path_for_workshop_mod(mod_1, mod_directory_1, workshop_id_1):
    """Test that workshop mods download to the Steam workshop content path."""
    # Not yet reviewed
    assert mod_1.download_path() == mod_directory_1 / 'steamapps' / 'workshop' / 'content' / '107410' / str(workshop_id_1)


def test__mod__download_path_uses_launch_parameter_for_manual_mod(manual_mod_1, mod_directory_1):
    """Test that manual mods download to the launch-parameter path."""
    # Not yet reviewed
    assert manual_mod_1.download_path() == mod_directory_1 / '@manual'


def test__modlist__stores_name_and_mods(mod_1, manual_mod_1, modlist_name_1):
    """Test that Modlist stores its name and mods."""
    # Not yet reviewed
    modlist = Modlist(modlist_name_1, mods=[mod_1, manual_mod_1])

    assert modlist.name == modlist_name_1
    assert modlist.mods == [mod_1, manual_mod_1]
    assert MODLISTS[modlist_name_1] is modlist


def test__modlist__loads_mods_from_file(tmp_path, mod_1, manual_mod_1, modlist_name_1):
    """Test that Modlist loads mod references from a file."""
    # Not yet reviewed
    MODS[mod_1.config_name] = mod_1
    MODS[manual_mod_1.config_name] = manual_mod_1
    modlist_file = tmp_path / 'main.txt'
    modlist_file.write_text(f'{mod_1.config_name}\n\n{manual_mod_1.config_name}\n')

    modlist = Modlist(modlist_name_1, file=modlist_file)

    assert modlist.mods == [mod_1, manual_mod_1]


def test__modlist__raises_when_file_references_unknown_mod(tmp_path, modlist_name_1):
    """Test that Modlist raises when a file references an unknown mod."""
    # Not yet reviewed
    modlist_file = tmp_path / 'main.txt'
    modlist_file.write_text('missing_mod\n')

    with pytest.raises(ModNotDefined):
        Modlist(modlist_name_1, file=modlist_file)


def test__modlist__has_mods_from_returns_true_for_overlap(mod_1, manual_mod_1):
    """Test that has_mods_from returns true when modlists overlap."""
    # Not yet reviewed
    modlist_1 = Modlist('main', mods=[mod_1])
    modlist_2 = Modlist('secondary', mods=[manual_mod_1, mod_1])

    assert modlist_1.has_mods_from(modlist_2) is True


def test__modlist__has_mods_from_returns_false_without_overlap(mod_1, manual_mod_1):
    """Test that has_mods_from returns false when modlists do not overlap."""
    # Not yet reviewed
    modlist = Modlist('main', mods=[mod_1])

    assert modlist.has_mods_from([manual_mod_1]) is False


def test__modlist__has_mods_from_rejects_invalid_type(mod_1):
    """Test that has_mods_from rejects unsupported inputs."""
    # Not yet reviewed
    modlist = Modlist('main', mods=[mod_1])

    with pytest.raises(TypeError):
        modlist.has_mods_from(object())
