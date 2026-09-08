# ruff: noqa: F811, F401

import pytest
from sqlalchemy import insert

from bw.auth.group import GroupStore
from bw.auth.permissions import Permissions
from bw.models.auth import Session
from integrations.fixtures import test_app
from integrations.missions.fixtures import (
    db_iteration_1,
    db_iteration_2,
    db_mission_1,
    db_mission_type_1,
    db_review_1,
    db_test_result_1,
    db_user_1,
    db_user_2,
)


@pytest.fixture(scope='session')
def mission_session_token():
    return 'mission-session-token'


@pytest.fixture(scope='function')
def db_mission_session(state, db_user_2, mission_session_token):
    with state.Session.begin() as session:
        query = insert(Session).values(user_id=db_user_2.id, token=mission_session_token, authenticated=True).returning(Session)
        user_session = session.execute(query).one()[0]
        session.expunge(user_session)
    yield user_session


@pytest.fixture(scope='function')
def db_mission_test_group(state, db_user_2):
    permission = GroupStore().create_permission(state, 'mission testers', Permissions(can_test_mission=True))
    group = GroupStore().create_group(state, 'mission testers', permission.name)
    GroupStore().assign_user_to_group(state, db_user_2, group)
    yield group


class TestMissionFrontendEndpoints:
    @pytest.mark.asyncio
    async def test__mission_page__renders_api_and_iteration_review_information(
        self,
        test_app,
        db_mission_session,
        mission_session_token,
        db_mission_1,
        db_iteration_1,
        db_review_1,
        db_test_result_1,
    ):
        response = await test_app.get(
            f'/missions/{db_mission_1.uuid}', headers={'Authorization': f'Bearer {mission_session_token}'}
        )
        html = await response.get_data(as_text=True)

        assert response.status_code == 200
        assert 'Mission information' in html
        assert str(db_mission_1.uuid) in html
        assert db_mission_1.creation_date.strftime('%Y-%m-%d %H:%M') in html
        assert 'Author UUID' not in html
        assert 'TVT' in html
        assert 'signoff needed' in html
        assert 'is_night' in html
        assert 'Iteration #1' in html
        assert db_iteration_1.file_name in html
        assert 'Reviews' in html
        assert str(db_test_result_1.uuid) in html
        assert 'Cosign this review' in html
        assert 'Testing temporarily disabled' in html
        assert f'/missions/{db_mission_1.uuid}/iterations/{db_iteration_1.uuid}/test' not in html

    @pytest.mark.asyncio
    async def test__test_iteration_page__renders_stub_review_form(
        self, test_app, db_mission_session, mission_session_token, db_mission_1, db_iteration_1
    ):
        response = await test_app.get(
            f'/missions/{db_mission_1.uuid}/iterations/{db_iteration_1.uuid}/test',
            headers={'Authorization': f'Bearer {mission_session_token}'},
        )
        html = await response.get_data(as_text=True)

        assert response.status_code == 200
        assert 'Overall result' in html
        assert 'Briefing and slotting' in html
        assert 'Loadouts and assets' in html
        assert 'Gameplay flow' in html
        assert 'Technical checks' in html
        assert 'Other considerations' in html
        assert f'/api/v1/html/missions/{db_mission_1.uuid}/iterations/{db_iteration_1.uuid}/test' in html
        assert 'Passed' in html
        assert 'Failed' in html


class TestMissionTestingApiEndpoints:
    @pytest.mark.asyncio
    async def test__test_iteration__creates_review_result(
        self, test_app, mission_session_token, db_mission_session, db_mission_test_group, db_iteration_1
    ):
        response = await test_app.post(
            f'/api/v1/missions/iteration/{db_iteration_1.uuid}/test',
            headers={'Authorization': f'Bearer {mission_session_token}'},
            json={'status': 'Passed', 'notes': {'briefing': 'looks good'}},
        )
        data = await response.get_json()

        assert response.status_code == 200
        assert 'result_uuid' in data

    @pytest.mark.asyncio
    async def test__cosign_review__creates_cosign(
        self, test_app, mission_session_token, db_mission_session, db_mission_test_group, db_test_result_1
    ):
        response = await test_app.post(
            f'/api/v1/missions/reviews/{db_test_result_1.uuid}/cosign',
            headers={'Authorization': f'Bearer {mission_session_token}'},
        )

        assert response.status_code == 201
