# ruff: noqa: F811, F401

import pytest
import json
import unittest
import re
import csv
import shutil
from bw.response import JsonResponse, Created, WebResponse
from bw.missions.api import MissionsApi, TestApi
from bw.error import CouldNotCreateIteration
from bw.missions.missions import MissionStore
from bw.missions.pbo import MissionLoader
from bw.missions.test_status import TestStatus
from bw.models.missions import TestCosign
from bw.auth.session import SessionStore
from integrations.missions.fixtures import (
    state,
    session,
    db_user_1,
    db_user_2,
    db_user_3,
    db_mission_type_1,
    fake_mission,
    fake_changelog,
    fake_iteration_1,
    fake_iteration_2,
    db_mission_1,
    db_iteration_1,
    db_iteration_2,
    db_review_1,
    db_review_2,
    db_test_result_1,
    db_test_result_1_2,
    db_test_result_2,
    db_test_cosign_1,
    invalid_uuid,
    test_notes,
    test_notes_multiple,
    metadata_1,
    disk_metadata_1,
    arma_server,
)


class TestMissionsApi:
    @pytest.mark.asyncio
    async def test__missions_api__upload_mission__success_with_new_upload(
        self, mocker, state, session, db_user_1, db_mission_type_1, fake_changelog, fake_iteration_1, fake_mission, arma_server
    ):
        mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
        mocker.patch.object(SessionStore, 'get_user_from_session_token', return_value=db_user_1)
        mocker.patch('bw.missions.api.shutil.copyfile', return_value=None)

        resp = await MissionsApi().upload_mission(state, arma_server, db_user_1, 'fake_path', fake_changelog)
        assert isinstance(resp, JsonResponse)
        assert resp.contained_json['iteration_number'] == 1
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test__missions_api__upload_mission__copy_file_already_exists_at_destination(
        self, mocker, state, session, db_user_1, db_mission_type_1, fake_changelog, fake_iteration_1, fake_mission, arma_server
    ):
        mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
        mocker.patch.object(SessionStore, 'get_user_from_session_token', return_value=db_user_1)
        mocker.patch('bw.missions.api.pathlib.Path.exists', return_value=True)

        resp = await MissionsApi().upload_mission(state, arma_server, db_user_1, 'fake_path', fake_changelog)
        assert not isinstance(resp, JsonResponse)
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test__missions_api__upload_mission__missing_metadata(
        self, mocker, state, session, fake_mission, fake_changelog, db_user_1, arma_server
    ):
        fake_mission.custom_attributes = {}
        mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
        mocker.patch('bw.missions.api.shutil.copyfile', return_value=None)
        resp = await MissionsApi().upload_mission(state, arma_server, db_user_1, 'fake_path', fake_changelog)
        assert not isinstance(resp, JsonResponse)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test__missions_api__upload_mission__missing_mission_type(
        self, mocker, state, session, fake_mission, fake_changelog, db_user_1, arma_server
    ):
        fake_mission.custom_attributes = {'potato_missiontesting_missionTestingInfo': {}}
        mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
        mocker.patch('bw.missions.api.shutil.copyfile', return_value=None)
        resp = await MissionsApi().upload_mission(state, arma_server, db_user_1, 'fake_path', fake_changelog)
        assert not isinstance(resp, JsonResponse)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test__missions_api__upload_mission__no_mission_type_with_tag(
        self, mocker, state, session, fake_mission, fake_changelog, db_user_1, arma_server
    ):
        mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
        mocker.patch('bw.missions.api.shutil.copyfile', return_value=None)
        resp = await MissionsApi().upload_mission(state, arma_server, db_user_1, 'fake_path', fake_changelog)
        assert not isinstance(resp, JsonResponse)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test__missions_api__upload_mission__could_not_create_iteration(
        self, mocker, state, session, db_user_1, db_mission_type_1, fake_mission, fake_changelog, arma_server
    ):
        mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
        mocker.patch.object(SessionStore, 'get_user_from_session_token', return_value=db_user_1)
        mocker.patch.object(MissionStore, 'add_iteration', side_effect=CouldNotCreateIteration())
        mocker.patch('bw.missions.api.shutil.copyfile', return_value=None)
        resp = await MissionsApi().upload_mission(state, arma_server, db_user_1, 'fake_path', fake_changelog)
        assert not isinstance(resp, JsonResponse)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test__missions_api__upload_mission__creates_new_mission(
        self, mocker, state, session, db_user_1, db_mission_type_1, fake_mission, fake_changelog, fake_iteration_1, arma_server
    ):
        mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
        mocker.patch.object(SessionStore, 'get_user_from_session_token', return_value=db_user_1)
        mocker.patch.object(MissionStore, 'add_iteration', return_value=fake_iteration_1)
        mocker.patch('bw.missions.api.shutil.copyfile', return_value=None)
        resp = await MissionsApi().upload_mission(state, arma_server, db_user_1, 'fake_path', fake_changelog)
        assert isinstance(resp, JsonResponse)
        assert resp.contained_json['iteration_number'] == 1
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test__missions_api__upload_mission__updates_existing_mission(
        self,
        mocker,
        state,
        session,
        db_user_1,
        db_mission_type_1,
        fake_mission,
        fake_changelog,
        fake_iteration_2,
        db_mission_1,
        arma_server,
    ):
        fake_mission.custom_attributes['potato_missionTesting_missionTestingInfo'] = {
            'potato_missionMaking_uuid': {'data': {'value': db_mission_1.uuid.hex}},
        }
        mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
        mocker.patch.object(SessionStore, 'get_user_from_session_token', return_value=db_user_1)
        mocker.patch.object(MissionStore, 'mission_with_uuid', return_value=db_mission_1)
        mocker.patch.object(MissionStore, 'add_iteration', return_value=fake_iteration_2)
        mocker.patch('bw.missions.api.shutil.copyfile', return_value=None)
        resp = await MissionsApi().upload_mission(state, arma_server, db_user_1, 'fake_path', fake_changelog)
        assert isinstance(resp, JsonResponse)
        assert resp.status_code == 201
        assert resp.contained_json['iteration_number'] == 2

    @pytest.mark.asyncio
    async def test__missions_api__upload_mission_metadata__success(self, mocker, fake_mission, tmp_path):
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
        assert isinstance(resp, Created)
        assert resp.status == '201 CREATED'
        assert mock_open.called

    @pytest.mark.asyncio
    async def test__missions_api__upload_mission_metadata__missing_metadata(self, mocker, fake_mission):
        fake_mission.custom_attributes = {}
        mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
        api = MissionsApi()
        resp = await api.upload_mission_metadata('fake_path')
        assert isinstance(resp, Created)
        assert resp.status == '201 CREATED'

    @pytest.mark.asyncio
    async def test__missions_api__upload_mission_metadata__missing_mission_type(self, mocker, fake_mission):
        fake_mission.custom_attributes = {'potato_missiontesting_missionTestingInfo': {}}
        mocker.patch.object(MissionLoader, 'load_pbo_from_directory', new=mocker.AsyncMock(return_value=fake_mission))
        api = MissionsApi()
        resp = await api.upload_mission_metadata('fake_path')
        assert isinstance(resp, Created)
        assert resp.status == '201 CREATED'

    @pytest.mark.asyncio
    async def test__missions_api__get_stored_metadata__success(self, mocker, disk_metadata_1, metadata_1):
        api = MissionsApi()
        mocker.patch.object(api, 'metadata_path', disk_metadata_1)

        resp = await api.get_stored_metadata()

        assert isinstance(resp, JsonResponse)
        assert resp.status_code == 200
        assert resp.contained_json['fields'] == metadata_1['fields']
        assert resp.contained_json['metadata'] == metadata_1['metadata']
        assert len(resp.contained_json['metadata']) == len(metadata_1['metadata'])

    @pytest.mark.asyncio
    async def test__missions_api__get_stored_metadata__returns_empty_on_no_file(self, mocker):
        api = MissionsApi()
        mocker.patch.object(api, 'metadata_path', '/nonexistent/path/log.csv')

        resp = await api.get_stored_metadata()

        assert isinstance(resp, JsonResponse)
        assert resp.status_code == 200
        assert resp.contained_json['fields'] == []
        assert resp.contained_json['metadata'] == []

    @pytest.mark.asyncio
    async def test__missions_api__get_stored_metadata__all_fields_found(self, mocker, disk_metadata_1, metadata_1):
        api = MissionsApi()
        mocker.patch.object(api, 'metadata_path', disk_metadata_1)

        resp = await api.get_stored_metadata()

        assert isinstance(resp, JsonResponse)
        assert resp.status_code == 200

        # Verify all expected fields are present
        assert resp.contained_json['fields'] == metadata_1['fields']

        # Verify specific field values from first entry
        first_entry = resp.contained_json['metadata'][0]
        assert first_entry['Mission Name'] == 'gn502_co30_TestMission_v1'
        assert first_entry['uuid'] == 'b3d7e343-d244-45fd-a614-a40e3da5de90'
        assert first_entry['tag'] == '1'

    @pytest.mark.asyncio
    async def test__missions_api__get_stored_metadata__returns_empty_on_csv_error(self, mocker, disk_metadata_1):
        api = MissionsApi()
        mocker.patch.object(api, 'metadata_path', disk_metadata_1)

        with unittest.mock.patch('bw.missions.api.csv.DictReader', side_effect=csv.Error):
            resp = await api.get_stored_metadata()

        assert isinstance(resp, JsonResponse)
        assert resp.status_code == 200
        assert resp.contained_json['fields'] == []
        assert resp.contained_json['metadata'] == []

    @pytest.mark.asyncio
    async def test__get_iteration_information__returns_full_mission_info(
        self, state, session, db_user_1, db_mission_type_1, db_mission_1, db_iteration_1
    ):
        iteration_information = await MissionsApi().get_iteration_information(state, iteration_uuid=db_iteration_1.uuid)
        mission_information = iteration_information['mission']
        type_information = mission_information['mission_type']

        assert iteration_information['uuid'] == str(db_iteration_1.uuid)
        assert iteration_information['min_player_count'] == db_iteration_1.min_player_count
        assert iteration_information['max_player_count'] == db_iteration_1.max_player_count
        assert iteration_information['desired_player_count'] == db_iteration_1.desired_player_count
        assert iteration_information['safe_start_length'] == db_iteration_1.safe_start_length
        assert iteration_information['mission_length'] == db_iteration_1.mission_length
        assert iteration_information['upload_date'] == db_iteration_1.upload_date.isoformat()
        assert iteration_information['bwmf_version'] == db_iteration_1.bwmf_version
        assert iteration_information['iteration'] == db_iteration_1.iteration
        assert iteration_information['changelog'] == db_iteration_1.changelog

        assert mission_information['uuid'] == str(db_mission_1.uuid)
        assert mission_information['server'] == db_mission_1.server
        assert mission_information['creation_date'] == db_mission_1.creation_date.isoformat()
        assert mission_information['author_uuid'] == str(db_user_1.uuid)
        assert mission_information['author_name'] == db_mission_1.author_name
        assert mission_information['title'] == db_mission_1.title
        assert mission_information['special_flags'] == db_mission_1.special_flags

        assert type_information['name'] == db_mission_type_1.name
        assert type_information['signoffs_required'] == db_mission_type_1.signoffs_required
        assert type_information['tag'] == db_mission_type_1.numeric_tag

    @pytest.mark.asyncio
    async def test__get_iteration_information__second_iteration_returns_full_mission_info(
        self, state, session, db_user_1, db_mission_type_1, db_mission_1, db_iteration_2
    ):
        iteration_information = await MissionsApi().get_iteration_information(state, iteration_uuid=db_iteration_2.uuid)
        mission_information = iteration_information['mission']
        type_information = mission_information['mission_type']

        assert iteration_information['uuid'] == str(db_iteration_2.uuid)
        assert iteration_information['min_player_count'] == db_iteration_2.min_player_count
        assert iteration_information['max_player_count'] == db_iteration_2.max_player_count
        assert iteration_information['desired_player_count'] == db_iteration_2.desired_player_count
        assert iteration_information['safe_start_length'] == db_iteration_2.safe_start_length
        assert iteration_information['mission_length'] == db_iteration_2.mission_length
        assert iteration_information['upload_date'] == db_iteration_2.upload_date.isoformat()
        assert iteration_information['bwmf_version'] == db_iteration_2.bwmf_version
        assert iteration_information['iteration'] == db_iteration_2.iteration
        assert iteration_information['changelog'] == db_iteration_2.changelog

        assert mission_information['uuid'] == str(db_mission_1.uuid)
        assert mission_information['server'] == db_mission_1.server
        assert mission_information['creation_date'] == db_mission_1.creation_date.isoformat()
        assert mission_information['author_uuid'] == str(db_user_1.uuid)
        assert mission_information['author_name'] == db_mission_1.author_name
        assert mission_information['title'] == db_mission_1.title
        assert mission_information['special_flags'] == db_mission_1.special_flags

        assert type_information['name'] == db_mission_type_1.name
        assert type_information['signoffs_required'] == db_mission_type_1.signoffs_required
        assert type_information['tag'] == db_mission_type_1.numeric_tag

    @pytest.mark.asyncio
    async def test__get_iteration_information__non_existent_iteration_returns_404(self, state, session, db_iteration_2):
        iteration_information = await MissionsApi().get_iteration_information(state, iteration_uuid=db_iteration_2.uuid)
        assert iteration_information.status == 404


# god i love naming conventions
class TestTestApi:
    @pytest.mark.asyncio
    async def test__test_api__review_mission__success(self, state, session, db_user_1, db_iteration_1, test_notes):
        api = TestApi()
        resp = await api.review_mission(state, db_user_1, db_iteration_1.uuid, TestStatus.PASSED, test_notes)

        assert isinstance(resp, JsonResponse)
        assert 'result_uuid' in resp.contained_json
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test__test_api__review_mission__success_with_multiple_notes(
        self, state, session, db_user_1, db_iteration_2, test_notes_multiple
    ):
        api = TestApi()
        resp = await api.review_mission(state, db_user_1, db_iteration_2.uuid, TestStatus.PASSED, test_notes_multiple)

        assert isinstance(resp, JsonResponse)
        assert 'result_uuid' in resp.contained_json
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test__test_api__review_mission__success_with_empty_notes(self, state, session, db_user_2, db_iteration_2):
        empty_notes = {}
        api = TestApi()
        resp = await api.review_mission(state, db_user_2, db_iteration_2.uuid, TestStatus.PASSED, empty_notes)

        assert isinstance(resp, JsonResponse)
        assert 'result_uuid' in resp.contained_json
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test__test_api__review_mission__iteration_not_found(self, state, session, db_user_1, invalid_uuid, test_notes):
        api = TestApi()
        resp = await api.review_mission(state, db_user_1, invalid_uuid, TestStatus.PASSED, test_notes)

        assert not isinstance(resp, JsonResponse)
        assert isinstance(resp, WebResponse)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test__test_api__review_mission__duplicate_review_same_user_same_iteration(
        self, state, session, db_user_1, db_iteration_1, test_notes, db_test_result_1
    ):
        # First review already exists via fixture db_test_result_1
        api = TestApi()
        resp = await api.review_mission(state, db_user_1, db_iteration_1.uuid, TestStatus.PASSED, test_notes)

        assert not isinstance(resp, JsonResponse)
        assert isinstance(resp, WebResponse)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test__test_api__cosign_result__success(self, state, session, db_user_2, db_test_result_1):
        api = TestApi()
        resp = await api.cosign_result(state, db_user_2, db_test_result_1.uuid)

        assert isinstance(resp, Created)
        assert resp.status == '201 CREATED'

    @pytest.mark.asyncio
    async def test__test_api__cosign_result__result_not_found(self, state, session, db_user_2, invalid_uuid):
        api = TestApi()
        resp = await api.cosign_result(state, db_user_2, invalid_uuid)

        assert not isinstance(resp, Created)
        assert isinstance(resp, WebResponse)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test__test_api__cosign_result__cannot_cosign_own_review(self, state, session, db_user_1, db_test_result_1):
        # db_test_result_1 is created by db_user_1 via db_review_1
        api = TestApi()
        resp = await api.cosign_result(state, db_user_1, db_test_result_1.uuid)

        assert not isinstance(resp, Created)
        assert isinstance(resp, WebResponse)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test__test_api__cosign_result__duplicate_cosign(
        self, state, session, db_user_2, db_test_result_1, db_test_cosign_1
    ):
        # db_test_cosign_1 already exists for this user and result
        api = TestApi()
        resp = await api.cosign_result(state, db_user_2, db_test_result_1.uuid)

        assert not isinstance(resp, Created)
        assert isinstance(resp, WebResponse)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test__test_api__reviews__success_with_viewer_as_reviewer(
        self, state, session, db_user_1, db_iteration_1, db_test_result_1
    ):
        api = TestApi()
        resp = await api.reviews(state, db_iteration_1.uuid, db_user_1)

        assert isinstance(resp, JsonResponse)
        assert 'reviews' in resp.contained_json
        assert len(resp.contained_json['reviews']) == 1
        review = resp.contained_json['reviews'][0]
        assert review['is_viewer_reviewer'] is True
        assert review['is_viewer_cosigner'] is False
        assert 'uuid' in review
        assert 'date_tested' in review
        assert 'status' in review
        assert 'notes' in review

    @pytest.mark.asyncio
    async def test__test_api__reviews__success_with_viewer_as_cosigner(
        self, state, session, db_user_2, db_iteration_1, db_test_result_1, db_test_cosign_1
    ):
        api = TestApi()
        resp = await api.reviews(state, db_iteration_1.uuid, db_user_2)

        assert isinstance(resp, JsonResponse)
        assert len(resp.contained_json['reviews']) == 1
        review = resp.contained_json['reviews'][0]
        assert review['is_viewer_reviewer'] is False
        assert review['is_viewer_cosigner'] is True

    @pytest.mark.asyncio
    async def test__test_api__reviews__success_with_no_viewer(self, state, session, db_iteration_1, db_test_result_1):
        api = TestApi()
        resp = await api.reviews(state, db_iteration_1.uuid, None)

        assert isinstance(resp, JsonResponse)
        assert len(resp.contained_json['reviews']) == 1
        review = resp.contained_json['reviews'][0]
        assert review['is_viewer_reviewer'] is False
        assert review['is_viewer_cosigner'] is False

    @pytest.mark.asyncio
    async def test__test_api__reviews__multiple_reviews_with_different_statuses(
        self, state, session, db_user_1, db_iteration_1, db_test_result_1, db_test_result_1_2
    ):
        # db_test_result_1 has PASSED status, db_test_result_1_2 has FAILED status
        api = TestApi()
        resp = await api.reviews(state, db_iteration_1.uuid, db_user_1)

        assert isinstance(resp, JsonResponse)
        assert len(resp.contained_json['reviews']) == 2

        # Verify different statuses are present
        statuses = [review['status'] for review in resp.contained_json['reviews']]
        assert TestStatus.PASSED in statuses
        assert TestStatus.FAILED in statuses

    @pytest.mark.asyncio
    async def test__test_api__reviews__empty_reviews_list(self, state, session, db_user_1, db_iteration_2):
        # db_iteration_2 has no test results
        api = TestApi()
        resp = await api.reviews(state, db_iteration_2.uuid, db_user_1)

        assert isinstance(resp, JsonResponse)
        assert resp.contained_json['reviews'] == []

    @pytest.mark.asyncio
    async def test__test_api__reviews__iteration_not_found(self, state, session, db_user_1, invalid_uuid):
        api = TestApi()
        resp = await api.reviews(state, invalid_uuid, db_user_1)

        assert not isinstance(resp, JsonResponse)
        assert isinstance(resp, WebResponse)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test__test_api__reviews__date_format_validation(self, state, session, db_user_1, db_iteration_1, db_test_result_1):
        api = TestApi()
        resp = await api.reviews(state, db_iteration_1.uuid, db_user_1)

        assert isinstance(resp, JsonResponse)
        review = resp.contained_json['reviews'][0]

        # Verify ISO format date
        iso_date_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$'
        assert re.match(iso_date_pattern, review['date_tested'])

    @pytest.mark.asyncio
    async def test__test_api__reviews__viewer_is_neither_reviewer_nor_cosigner(
        self, state, session, db_user_3, db_iteration_1, db_test_result_1_2
    ):
        # db_test_result_1_2 is by db_user_2, viewing as db_user_3
        api = TestApi()
        resp = await api.reviews(state, db_iteration_1.uuid, db_user_3)

        assert isinstance(resp, JsonResponse)
        reviews = resp.contained_json['reviews']

        # Verify all reviews show user3 as neither reviewer nor cosigner
        for review in reviews:
            assert review['is_viewer_reviewer'] is False
            assert review['is_viewer_cosigner'] is False

    @pytest.mark.asyncio
    async def test__test_api__reviews__viewer_both_reviewer_and_cosigner_different_reviews(
        self, state, session, db_user_1, db_user_2, db_iteration_1, db_test_result_1, db_test_result_1_2
    ):
        # Create a cosign for user1 on the review by user2
        with state.Session.begin() as session:
            cosign = TestCosign(test_result_id=db_test_result_1_2.id, tester_id=db_user_1.id)
            session.add(cosign)
            session.flush()

        api = TestApi()
        resp = await api.reviews(state, db_iteration_1.uuid, db_user_1)

        assert isinstance(resp, JsonResponse)
        reviews = resp.contained_json['reviews']
        assert len(reviews) == 2

        # One review should have user1 as reviewer, another as cosigner
        reviewer_count = sum(1 for r in reviews if r['is_viewer_reviewer'])
        cosigner_count = sum(1 for r in reviews if r['is_viewer_cosigner'])
        assert reviewer_count == 1
        assert cosigner_count == 1
