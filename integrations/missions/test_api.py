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
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test__missions_api__upload_mission_to_main__missing_metadata(mocker, state, session, fake_mission, fake_changelog):
    fake_mission.custom_attributes = {}
    mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
    resp = await MissionsApi().upload_mission_to_main(state, 'token', 'fake_path', fake_changelog)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test__missions_api__upload_mission_to_main__missing_mission_type(mocker, state, session, fake_mission, fake_changelog):
    fake_mission.custom_attributes = {'potato_missiontesting_missionTestingInfo': {}}
    mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
    resp = await MissionsApi().upload_mission_to_main(state, 'token', 'fake_path', fake_changelog)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test__missions_api__upload_mission_to_main__no_mission_type_with_tag(
    mocker, state, session, fake_mission, fake_changelog
):
    mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
    resp = await MissionsApi().upload_mission_to_main(state, 'token', 'fake_path', fake_changelog)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test__missions_api__upload_mission_to_main__invalid_session(
    mocker, state, session, db_mission_type_1, fake_mission, fake_changelog
):
    mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
    resp = await MissionsApi().upload_mission_to_main(state, 'token', 'fake_path', fake_changelog)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test__missions_api__upload_mission_to_main__could_not_create_iteration(
    mocker, state, session, db_user_1, db_mission_type_1, fake_mission, fake_changelog
):
    mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
    mocker.patch.object(SessionStore, 'get_user_from_session_token', return_value=db_user_1)
    mocker.patch.object(MissionStore, 'add_iteration', side_effect=CouldNotCreateIteration())
    resp = await MissionsApi().upload_mission_to_main(state, 'token', 'fake_path', fake_changelog)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test__missions_api__upload_mission_to_main__creates_new_mission(
    mocker, state, session, db_user_1, db_mission_type_1, fake_mission, fake_changelog, fake_iteration_1
):
    mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
    mocker.patch.object(SessionStore, 'get_user_from_session_token', return_value=db_user_1)
    mocker.patch.object(MissionStore, 'add_iteration', return_value=fake_iteration_1)
    resp = await MissionsApi().upload_mission_to_main(state, 'token', 'fake_path', fake_changelog)
    assert resp.contained_json['iteration_number'] == 1
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test__missions_api__upload_mission_to_main__updates_existing_mission(
    mocker, state, session, db_user_1, db_mission_type_1, fake_mission, fake_changelog, fake_iteration_2, db_mission_1
):
    fake_mission.custom_attributes['potato_missionTesting_missionTestingInfo'] = {
        'potato_missionMaking_uuid': {'data': {'value': db_mission_1.uuid.hex}},
    }
    mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
    mocker.patch.object(SessionStore, 'get_user_from_session_token', return_value=db_user_1)
    mocker.patch.object(MissionStore, 'mission_with_uuid', return_value=db_mission_1)
    mocker.patch.object(MissionStore, 'add_iteration', return_value=fake_iteration_2)
    resp = await MissionsApi().upload_mission_to_main(state, 'token', 'fake_path', fake_changelog)
    assert resp.status_code == 201
    assert resp.contained_json['iteration_number'] == 2


@pytest.mark.asyncio
async def test__missions_api__upload_mission_metadata__success(mocker, fake_mission, tmp_path):
    # Setup: ensure metadata dir exists and is empty
    metadata_dir = tmp_path / 'metadata'
    metadata_dir.mkdir()
    mocker.patch(
        'bw.missions.api.os.path.exists', side_effect=lambda p: p == str(metadata_dir) or p == str(metadata_dir / 'log.csv')
    )
    mocker.patch('bw.missions.api.os.makedirs')
    mocker.patch('bw.missions.api.os.path.getsize', return_value=0)
    mocker.patch('bw.missions.api.os.remove')
    mocker.patch('bw.missions.api.GLOBAL_CONFIGURATION', {'mission_metadata_csv_size': 2 * 1024 * 1024 * 1024})
    mock_open = mocker.patch('bw.missions.api.open', mocker.mock_open(), create=True)
    mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
    api = MissionsApi()
    resp = await api.upload_mission_metadata('fake_path')
    assert resp.status == '201 CREATED'
    assert mock_open.called


@pytest.mark.asyncio
async def test__missions_api__upload_mission_metadata__missing_metadata(mocker, fake_mission):
    fake_mission.custom_attributes = {}
    mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
    api = MissionsApi()
    resp = await api.upload_mission_metadata('fake_path')
    assert resp.status == '422 UNPROCESSABLE ENTITY'


@pytest.mark.asyncio
async def test__missions_api__upload_mission_metadata__missing_mission_type(mocker, fake_mission):
    fake_mission.custom_attributes = {'potato_missiontesting_missionTestingInfo': {}}
    mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
    api = MissionsApi()
    resp = await api.upload_mission_metadata('fake_path')
    assert resp.status == '422 UNPROCESSABLE ENTITY'
