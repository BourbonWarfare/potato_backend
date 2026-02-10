# ruff: noqa: F811, F401

import pytest
import datetime

from sqlalchemy import insert

from bw.server_ops.arma.mod import Mod, SteamWorkshopDetails, WorkshopId, Modlist
from bw.models.arma import Mod as DbMod
from integrations.fixtures import session, state


@pytest.fixture(scope='session')
def workshop_details_1():
    return SteamWorkshopDetails(
        workshop_id=WorkshopId(463939057),
        title='ACE3',
        file_size_bytes=1024000,
        last_update=datetime.datetime(2023, 1, 1, 12, 0, 0),
    )


@pytest.fixture(scope='session')
def workshop_details_2():
    return SteamWorkshopDetails(
        workshop_id=WorkshopId(450814997),
        title='CBA_A3',
        file_size_bytes=512000,
        last_update=datetime.datetime(2023, 2, 1, 12, 0, 0),
    )


@pytest.fixture(scope='session')
def workshop_details_3():
    return SteamWorkshopDetails(
        workshop_id=WorkshopId(2987557792),
        title='Potato',
        file_size_bytes=512000,
        last_update=datetime.datetime(2023, 6, 10, 15, 33, 0),
    )


@pytest.fixture(scope='session')
def updated_workshop_details_1(workshop_details_1):
    return SteamWorkshopDetails(
        workshop_id=workshop_details_1.workshop_id,
        title=workshop_details_1.title,
        file_size_bytes=workshop_details_1.file_size_bytes + 12344,
        last_update=datetime.datetime(2023, 6, 1, 12, 0, 0),
    )


@pytest.fixture(scope='session')
def updated_workshop_details_2(workshop_details_2):
    return SteamWorkshopDetails(
        workshop_id=workshop_details_2.workshop_id,
        title=workshop_details_2.title,
        file_size_bytes=workshop_details_2.file_size_bytes + 1244,
        last_update=datetime.datetime(2024, 6, 1, 12, 0, 0),
    )


@pytest.fixture(scope='session')
def null_mod():
    return Mod()


@pytest.fixture(scope='session')
def mod_1(workshop_details_1):
    return Mod(
        name=workshop_details_1.title,
        workshop_id=workshop_details_1.workshop_id,
    )


@pytest.fixture(scope='session')
def mod_2(workshop_details_2):
    return Mod(
        name=workshop_details_2.title,
        workshop_id=workshop_details_2.workshop_id,
    )


@pytest.fixture(scope='session')
def mod_3(workshop_details_3):
    return Mod(
        name=workshop_details_3.title,
        workshop_id=workshop_details_3.workshop_id,
    )


@pytest.fixture(scope='function')
def db_mod_1(state, session, workshop_details_1):
    with state.Session.begin() as session:
        db_mod = DbMod.from_workshop_details(workshop_details_1)
        session.add(db_mod)
        session.flush()
        session.expunge(db_mod)
    yield db_mod


@pytest.fixture(scope='function')
def db_mod_2(state, session, workshop_details_2):
    with state.Session.begin() as session:
        db_mod = DbMod.from_workshop_details(workshop_details_2)
        session.add(db_mod)
        session.flush()
        session.expunge(db_mod)
    yield db_mod


@pytest.fixture(scope='function')
def db_mod_3(state, session, workshop_details_3):
    with state.Session.begin() as session:
        db_mod = DbMod.from_workshop_details(workshop_details_3)
        session.add(db_mod)
        session.flush()
        session.expunge(db_mod)
    yield db_mod


@pytest.fixture(scope='session')
def mock_mod_name_1():
    return 'mod1'


@pytest.fixture(scope='session')
def mock_mod_name_2():
    return 'mod2'


@pytest.fixture(scope='session')
def mock_mod_name_3():
    return 'new_mod'


@pytest.fixture(scope='session')
def mock_workshop_id_1():
    return 123


@pytest.fixture(scope='session')
def mock_workshop_id_2():
    return 456


@pytest.fixture(scope='session')
def mock_workshop_id_3():
    return 123456


@pytest.fixture(scope='session')
def mock_mod_1(mock_mod_name_1, mock_workshop_id_1):
    return Mod(name=mock_mod_name_1, workshop_id=WorkshopId(mock_workshop_id_1))


@pytest.fixture(scope='session')
def mock_mod_2(mock_mod_name_2, mock_workshop_id_2):
    return Mod(name=mock_mod_name_2, workshop_id=WorkshopId(mock_workshop_id_2))


@pytest.fixture(scope='session')
def mock_modlist_name_1():
    return 'test_list'


@pytest.fixture(scope='session')
def mock_modlist_name_2():
    return 'list1'


@pytest.fixture(scope='session')
def mock_modlist_name_3():
    return 'list2'


@pytest.fixture(scope='session')
def mock_modlist_name_4():
    return 'new_list'


@pytest.fixture(scope='session')
def mock_modlist_name_5():
    return 'existing_list'


@pytest.fixture(scope='session')
def mock_modlist_name_6():
    return 'empty_list'


@pytest.fixture(scope='session')
def mock_modlist_1(mock_modlist_name_1, mock_mod_1, mock_mod_2):
    return Modlist(name=mock_modlist_name_1, mods=[mock_mod_1, mock_mod_2])


@pytest.fixture(scope='session')
def mock_modlist_2(mock_modlist_name_2, mock_mod_1):
    return Modlist(name=mock_modlist_name_2, mods=[mock_mod_1])


@pytest.fixture(scope='session')
def mock_modlist_3(mock_modlist_name_3, mock_mod_1, mock_mod_2):
    return Modlist(name=mock_modlist_name_3, mods=[mock_mod_1, mock_mod_2])


@pytest.fixture(scope='session')
def mock_modlist_4(mock_modlist_name_5, mock_mod_1):
    return Modlist(name=mock_modlist_name_5, mods=[mock_mod_1])


@pytest.fixture(scope='session')
def server_name_1():
    return 'test_server'


@pytest.fixture(scope='session')
def server_name_2():
    return 'nonexistent_server'


@pytest.fixture(scope='session')
def existing_mod_name():
    return 'existing_mod'


@pytest.fixture(scope='session')
def nonexistent_mod_name():
    return 'nonexistent_mod'


@pytest.fixture(scope='session')
def test_config_path():
    from pathlib import Path

    return Path('/test/path')


@pytest.fixture(scope='session')
def invalid_kind():
    return 'invalid_kind'


@pytest.fixture(scope='session')
def duplicate_workshop_id():
    return 123456


# Endpoint URL fixtures


@pytest.fixture(scope='session')
def endpoint_arma_base_url():
    return '/api/v1/server_ops/arma'


@pytest.fixture(scope='session')
def endpoint_mods_url(endpoint_arma_base_url):
    return f'{endpoint_arma_base_url}/mods'


@pytest.fixture(scope='session')
def endpoint_server_mods_url(endpoint_arma_base_url, server_name_1):
    return f'{endpoint_arma_base_url}/mods/{server_name_1}'


@pytest.fixture(scope='session')
def endpoint_modlists_url(endpoint_arma_base_url):
    return f'{endpoint_arma_base_url}/mods/lists'


@pytest.fixture(scope='session')
def endpoint_server_modlist_url(endpoint_arma_base_url, server_name_1):
    return f'{endpoint_arma_base_url}/mods/list/{server_name_1}'


@pytest.fixture(scope='session')
def endpoint_reload_mods_url(endpoint_arma_base_url):
    return f'{endpoint_arma_base_url}/mods/reload'


@pytest.fixture(scope='session')
def endpoint_reload_modlists_url(endpoint_arma_base_url):
    return f'{endpoint_arma_base_url}/mods/lists/reload'
