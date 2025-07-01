# ruff: noqa: F811, F401

import pytest
from bw.missions.api import MissionsApi
from bw.error import CouldNotCreateIteration, CouldNotCreateMissionType
from bw.missions.missions import MissionStore, MissionTypeStore
from bw.missions.pbo import MissionLoader
from bw.auth.session import SessionStore
from integrations.missions.fixtures import (
    state,
    session,
    db_user_1,
    db_mission_type_1,
    fake_mission,
    fake_changelog,
    fake_iteration_1,
    fake_iteration_2,
    db_mission_1,
)


@pytest.mark.asyncio
async def test__missions_api__upload_mission_to_main__success_with_new_upload(
    mocker, state, session, db_user_1, db_mission_type_1, fake_changelog, fake_iteration_1, fake_mission
):
    mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
    mocker.patch.object(SessionStore, 'get_user_from_session_token', return_value=db_user_1)

    resp = await MissionsApi().upload_mission_to_main(state, 'token', 'fake_path', fake_changelog)
    assert resp.contained_json['iteration_number'] == 1
    assert resp.contained_json['status'] == 200


@pytest.mark.asyncio
async def test__missions_api__upload_mission_to_main__missing_metadata(mocker, state, session, fake_mission, fake_changelog):
    fake_mission.custom_attributes = {}
    mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
    resp = await MissionsApi().upload_mission_to_main(state, 'token', 'fake_path', fake_changelog)
    assert resp.contained_json['status'] == 422


@pytest.mark.asyncio
async def test__missions_api__upload_mission_to_main__missing_mission_type(mocker, state, session, fake_mission, fake_changelog):
    fake_mission.custom_attributes = {'potato_missiontesting_missionTestingInfo': {}}
    mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
    resp = await MissionsApi().upload_mission_to_main(state, 'token', 'fake_path', fake_changelog)
    assert resp.contained_json['status'] == 422


@pytest.mark.asyncio
async def test__missions_api__upload_mission_to_main__no_mission_type_with_tag(
    mocker, state, session, fake_mission, fake_changelog
):
    mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
    resp = await MissionsApi().upload_mission_to_main(state, 'token', 'fake_path', fake_changelog)
    assert resp.contained_json['status'] == 404


@pytest.mark.asyncio
async def test__missions_api__upload_mission_to_main__invalid_session(
    mocker, state, session, db_mission_type_1, fake_mission, fake_changelog
):
    mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
    resp = await MissionsApi().upload_mission_to_main(state, 'token', 'fake_path', fake_changelog)
    assert resp.contained_json['status'] == 403


@pytest.mark.asyncio
async def test__missions_api__upload_mission_to_main__could_not_create_iteration(
    mocker, state, session, db_user_1, db_mission_type_1, fake_mission, fake_changelog
):
    mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
    mocker.patch.object(SessionStore, 'get_user_from_session_token', return_value=db_user_1)
    mocker.patch.object(MissionStore, 'add_iteration', side_effect=CouldNotCreateIteration())
    resp = await MissionsApi().upload_mission_to_main(state, 'token', 'fake_path', fake_changelog)
    assert resp.contained_json['status'] == 400


@pytest.mark.asyncio
async def test__missions_api__upload_mission_to_main__creates_new_mission(
    mocker, state, session, db_user_1, db_mission_type_1, fake_mission, fake_changelog, fake_iteration_1
):
    mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
    mocker.patch.object(SessionStore, 'get_user_from_session_token', return_value=db_user_1)
    mock_add_iteration = mocker.patch.object(MissionStore, 'add_iteration')
    mock_add_iteration.return_value = fake_iteration_1
    resp = await MissionsApi().upload_mission_to_main(state, 'token', 'fake_path', fake_changelog)
    assert resp.contained_json['iteration_number'] == 1
    assert resp.contained_json['status'] == 200


@pytest.mark.asyncio
async def test__missions_api__upload_mission_to_main__updates_existing_mission(
    mocker, state, session, db_user_1, db_mission_type_1, fake_mission, fake_changelog, fake_iteration_2, db_mission_1
):
    fake_mission.custom_attributes['potato_missionMaking_metadata'] = {
        'potato_missionMaking_uuid': {'Value': {'data': {'value': db_mission_1.uuid.hex}}},
    }
    mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
    mocker.patch.object(SessionStore, 'get_user_from_session_token', return_value=db_user_1)
    mocker.patch.object(MissionStore, 'mission_with_uuid', return_value=db_mission_1)
    mock_add_iteration = mocker.patch.object(MissionStore, 'add_iteration')
    mock_add_iteration.return_value = fake_iteration_2
    resp = await MissionsApi().upload_mission_to_main(state, 'token', 'fake_path', fake_changelog)
    assert resp.contained_json['status'] == 200
    assert resp.contained_json['iteration_number'] == 2
