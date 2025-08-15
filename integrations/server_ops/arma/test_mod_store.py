# ruff: noqa: F811, F401

import pytest
import datetime
from sqlalchemy import insert, select

from bw.server_ops.arma.mod_store import ModStore
from bw.server_ops.arma.mod import SteamWorkshopDetails, WorkshopId, Mod
from bw.models.arma import Mod as DbMod
from bw.error.arma_mod import (
    ModFieldInvalid,
    ModAlreadyExists,
    ModCreationFailed,
    ModNotFound,
)
from integrations.fixtures import session, state
from integrations.server_ops.arma.fixtures import (
    workshop_details_1,
    workshop_details_2,
    workshop_details_3,
    updated_workshop_details_1,
    updated_workshop_details_2,
    mod_1,
    mod_2,
    null_mod,
    db_mod_1,
    db_mod_2,
    db_mod_3,
)


def test__create_mod__success(session, state, workshop_details_1):
    result = ModStore().create_mod(state, workshop_details_1)

    assert result.workshop_id == workshop_details_1.workshop_id
    assert result.last_update_date == int(workshop_details_1.last_update.timestamp())


def test__create_mod__duplicate_raises(session, state, workshop_details_1, db_mod_1):
    with pytest.raises(ModAlreadyExists):
        ModStore().create_mod(state, workshop_details_1)


def test__get_mod_by_workshop_id__success(session, state, db_mod_1):
    result = ModStore().get_mod_by_workshop_id(state, db_mod_1.workshop_id)

    assert result.workshop_id == db_mod_1.workshop_id
    assert result.last_update_date == db_mod_1.last_update_date


def test__get_mod_by_workshop_id__not_found_raises(session, state):
    with pytest.raises(ModNotFound):
        ModStore().get_mod_by_workshop_id(state, WorkshopId(0))


def test__update_mod__success(session, state, db_mod_1, updated_workshop_details_1):
    result = ModStore().update_mod(state, updated_workshop_details_1)

    assert result.workshop_id == updated_workshop_details_1.workshop_id
    assert result.last_update_date == int(updated_workshop_details_1.last_update.timestamp())

    existing_mod = ModStore().get_mod_by_workshop_id(state, result.workshop_id)
    assert existing_mod.last_update_date == int(updated_workshop_details_1.last_update.timestamp())


def test__update_mod__not_found_raises(session, state, workshop_details_1):
    with pytest.raises(ModNotFound):
        ModStore().update_mod(state, workshop_details_1)


def test__get_out_of_date_mods__success(session, state, db_mod_1, db_mod_2, workshop_details_2, updated_workshop_details_1):
    result = ModStore().get_out_of_date_mods(state, [updated_workshop_details_1, workshop_details_2])

    assert len(result) == 1
    assert result[0].workshop_id == db_mod_1.workshop_id


def test__get_out_of_date_mods__no_out_of_date_mods(session, state, db_mod_1, db_mod_2, workshop_details_2, workshop_details_1):
    result = ModStore().get_out_of_date_mods(state, [workshop_details_1, workshop_details_2])

    assert len(result) == 0


def test__get_out_of_date_mods__only_returns_mods_given(session, state, db_mod_1, db_mod_2, updated_workshop_details_1):
    result = ModStore().get_out_of_date_mods(state, [updated_workshop_details_1])

    assert len(result) == 1
    assert result[0].workshop_id == db_mod_1.workshop_id


def test__get_all_mods__success(session, state, db_mod_1, db_mod_2):
    result = ModStore().get_all_mods(state)

    assert len(result) == 2
    workshop_ids = [mod.workshop_id for mod in result]
    assert db_mod_1.workshop_id in workshop_ids
    assert db_mod_2.workshop_id in workshop_ids


def test__get_all_mods__no_mods_empty(session, state):
    result = ModStore().get_all_mods(state)

    assert len(result) == 0


def test__delete_mod__success_with_steam_workshop_details(session, state, db_mod_1, db_mod_2, workshop_details_1):
    ModStore().delete_mod(state, workshop_details_1)

    with pytest.raises(ModNotFound):
        ModStore().get_mod_by_workshop_id(state, workshop_details_1.workshop_id)

    result = ModStore().get_mod_by_workshop_id(state, db_mod_2.workshop_id)
    assert result.workshop_id == db_mod_2.workshop_id


def test__delete_mod__success_with_mod_object(session, state, db_mod_1, db_mod_2, mod_1):
    ModStore().delete_mod(state, mod_1)

    with pytest.raises(ModNotFound):
        ModStore().get_mod_by_workshop_id(state, mod_1.workshop_id)

    result = ModStore().get_mod_by_workshop_id(state, db_mod_2.workshop_id)
    assert result.workshop_id == db_mod_2.workshop_id


def test__delete_mod__success_with_workshop_id(session, state, db_mod_1, db_mod_2, workshop_details_1):
    ModStore().delete_mod(state, workshop_details_1.workshop_id)

    with pytest.raises(ModNotFound):
        ModStore().get_mod_by_workshop_id(state, workshop_details_1.workshop_id)

    result = ModStore().get_mod_by_workshop_id(state, db_mod_2.workshop_id)
    assert result.workshop_id == db_mod_2.workshop_id


def test__delete_mod__no_mod_nothing(session, state, db_mod_1, db_mod_2, null_mod):
    with pytest.raises(ModFieldInvalid):
        ModStore().delete_mod(state, null_mod)


def test__bulk_update__success(
    session, state, db_mod_1, db_mod_2, db_mod_3, updated_workshop_details_1, updated_workshop_details_2
):
    result = ModStore().bulk_update_mods(state, [updated_workshop_details_1, updated_workshop_details_2])

    assert len(result) == 2
    assert result[0].workshop_id == updated_workshop_details_1.workshop_id
    assert result[0].last_update_date == int(updated_workshop_details_1.last_update.timestamp())
    assert result[1].workshop_id == updated_workshop_details_2.workshop_id
    assert result[1].last_update_date == int(updated_workshop_details_2.last_update.timestamp())


def test__bulk_update__no_mod_fails(session, state, db_mod_1, db_mod_3, updated_workshop_details_1, updated_workshop_details_2):
    with pytest.raises(ModNotFound):
        ModStore().bulk_update_mods(state, [updated_workshop_details_1, updated_workshop_details_2])


def test__bulk_update__no_updates_success(session, state, db_mod_1, db_mod_2, db_mod_3):
    result = ModStore().bulk_update_mods(state, [])

    assert len(result) == 0
