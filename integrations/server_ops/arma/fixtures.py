# ruff: noqa: F811, F401

import pytest
import datetime

from sqlalchemy import insert

from bw.server_ops.arma.mod import Mod, SteamWorkshopDetails, WorkshopId
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
