# ruff: noqa: F811, F401

import pytest
import uuid
import tempfile
import csv
from pathlib import Path

from sqlalchemy import insert

from bw.models.auth import User
from bw.models.missions import Mission, MissionType, Iteration, Review, TestResult, TestCosign
from bw.missions.test_status import TestStatus
from bw.server_ops.arma.server import Server
from bw.configuration import Configuration
from integrations.fixtures import session, state


@pytest.fixture
def fake_mission():
    class FakeMission:
        def __init__(self):
            self.custom_attributes = {
                'potato_missiontesting_missionTestingInfo': {
                    'potato_missiontesting_missionType': {'data': {'value': 1}},
                    'potato_missionMaking_uuid': {'data': {'value': 'b3d7e343-d244-45fd-a614-a40e3da5de90'}},
                },
            }
            self.author = 'author_name'
            self.source_name = 'mission_v1'
            self.bwmf = '1.0.0'

    return FakeMission()


@pytest.fixture
def fake_changelog():
    return {'changes': 'Initial commit'}


@pytest.fixture
def fake_iteration_1():
    return type('FakeIteration', (), {'iteration': 1})()


@pytest.fixture
def fake_iteration_2():
    return type('FakeIteration', (), {'iteration': 2})()


@pytest.fixture(scope='function')
def db_user_1(state, session):
    with state.Session.begin() as session:
        query = insert(User).values(id=1).returning(User)
        user = session.execute(query).first()[0]
        session.expunge(user)
    yield user


@pytest.fixture(scope='function')
def db_user_2(state, session):
    with state.Session.begin() as session:
        query = insert(User).values(id=2).returning(User)
        user = session.execute(query).first()[0]
        session.expunge(user)
    yield user


@pytest.fixture(scope='function')
def db_user_3(state, session):
    with state.Session.begin() as session:
        query = insert(User).values(id=3).returning(User)
        user = session.execute(query).first()[0]
        session.expunge(user)
    yield user


@pytest.fixture(scope='function')
def db_mission_type_1(state, session):
    with state.Session.begin() as session:
        mission_type = MissionType(name='TVT', signoffs_required=1, numeric_tag=1)
        session.add(mission_type)
        session.flush()
        session.expunge(mission_type)
    yield mission_type


@pytest.fixture(scope='function')
def db_mission_type_2(state, session):
    with state.Session.begin() as session:
        mission_type = MissionType(name='LONG COOP', signoffs_required=2, numeric_tag=3)
        session.add(mission_type)
        session.flush()
        session.expunge(mission_type)
    yield mission_type


@pytest.fixture(scope='function')
def db_mission_1(state, session, db_user_1, db_mission_type_1):
    with state.Session.begin() as session:
        mission = Mission(
            id=1,
            server='main',
            uuid=uuid.UUID('b3d7e343-d244-45fd-a614-a40e3da5de90'),
            author=db_user_1.id,
            author_name='me',
            title='foobar',
            mission_type=db_mission_type_1.id,
            special_flags={'is_night': True},
        )
        session.add(mission)
        session.flush()
        session.expunge(mission)
    yield mission


@pytest.fixture(scope='function')
def db_mission_1_1(state, session, db_user_1, db_mission_type_2):
    with state.Session.begin() as session:
        mission = Mission(
            id=2,
            server='main',
            uuid=uuid.UUID('c3d7e343-d244-45fd-a614-a40e3da5de91'),
            author=db_user_1.id,
            author_name='me',
            title='foobar 2',
            mission_type=db_mission_type_2.id,
            special_flags={'is_night': True},
        )
        session.add(mission)
        session.flush()
        session.expunge(mission)
    yield mission


@pytest.fixture(scope='function')
def db_mission_1_2(state, session, db_user_1, db_mission_type_1):
    with state.Session.begin() as session:
        mission = Mission(
            id=3,
            server='main',
            uuid=uuid.UUID('d3d7e343-d244-45fd-a614-a40e3da5de92'),
            author=db_user_1.id,
            author_name='me',
            title='foobar',
            mission_type=db_mission_type_1.id,
            special_flags={'is_night': True},
        )
        session.add(mission)
        session.flush()
        session.expunge(mission)
    yield mission


@pytest.fixture(scope='function')
def db_iteration_1(state, session, db_mission_1):
    with state.Session.begin() as session:
        iteration = Iteration(
            file_name='iteration.pbo',
            mission_id=db_mission_1.id,
            min_player_count=1,
            max_player_count=10,
            desired_player_count=5,
            iteration=1,
            mission_length=70,
            bwmf_version='1.0.0',
            changelog={'changes': 'Updated mission file'},
        )
        session.add(iteration)
        session.flush()
        session.expunge(iteration)
    yield iteration


@pytest.fixture(scope='function')
def db_iteration_2(state, session, db_mission_1):
    with state.Session.begin() as session:
        iteration = Iteration(
            file_name='iteration.pbo',
            mission_id=db_mission_1.id,
            min_player_count=1,
            max_player_count=10,
            desired_player_count=5,
            iteration=2,
            mission_length=70,
            bwmf_version='1.0.0',
            changelog={'changes': 'Updated mission file again'},
        )
        session.add(iteration)
        session.flush()
        session.expunge(iteration)
    yield iteration


@pytest.fixture(scope='function')
def db_review_1(state, session, db_user_1):
    with state.Session.begin() as session:
        review = Review(tester_id=db_user_1.id, status=TestStatus.PASSED, notes={'briefing': 'i understand now'})
        session.add(review)
        session.flush()
        session.expunge(review)
    yield review


@pytest.fixture(scope='function')
def db_review_2(state, session, db_user_2):
    with state.Session.begin() as session:
        review = Review(tester_id=db_user_2.id, status=TestStatus.FAILED, notes={'briefing': 'i dont understand now'})
        session.add(review)
        session.flush()
        session.expunge(review)
    yield review


@pytest.fixture(scope='function')
def db_test_result_1(state, session, db_review_1, db_iteration_1):
    with state.Session.begin() as session:
        test_result = TestResult(review_id=db_review_1.id, iteration_id=db_iteration_1.id)
        session.add(test_result)
        session.flush()
        session.expunge(test_result)
    yield test_result


@pytest.fixture(scope='function')
def db_test_result_1_2(state, session, db_review_2, db_iteration_1):
    with state.Session.begin() as session:
        test_result = TestResult(review_id=db_review_2.id, iteration_id=db_iteration_1.id)
        session.add(test_result)
        session.flush()
        session.expunge(test_result)
    yield test_result


@pytest.fixture(scope='function')
def db_test_result_2(state, session, db_review_2, db_iteration_2):
    with state.Session.begin() as session:
        test_result = TestResult(review_id=db_review_2.id, iteration_id=db_iteration_2.id)
        session.add(test_result)
        session.flush()
        session.expunge(test_result)
    yield test_result


@pytest.fixture(scope='function')
def db_test_cosign_1(state, session, db_test_result_1, db_user_2):
    with state.Session.begin() as session:
        test_cosign = TestCosign(test_result_id=db_test_result_1.id, tester_id=db_user_2.id)
        session.add(test_cosign)
        session.flush()
        session.expunge(test_cosign)
    yield test_cosign


@pytest.fixture
def invalid_uuid():
    return uuid.UUID('00000000-0000-0000-0000-000000000000')


@pytest.fixture
def test_notes():
    return {'briefing': 'good mission', 'gameplay': 'balanced'}


@pytest.fixture
def test_notes_multiple():
    return {'briefing': 'excellent', 'gameplay': 'balanced', 'mission_flow': 'smooth'}


@pytest.fixture
def metadata_1():
    return {
        'fields': [
            'Mission Name',
            'Has `missionTestingInfo`',
            'Has `missionType`',
            'uuid',
            'tag',
            'flag1',
            'flag2',
            'flag3',
            'minPlayers',
            'desiredPlayers',
            'maxPlayers',
            'safeStartTime',
            'missionTime',
        ],
        'metadata': [
            {
                'Mission Name': 'gn502_co30_TestMission_v1',
                'Has `missionTestingInfo`': '1',
                'Has `missionType`': '1',
                'uuid': 'b3d7e343-d244-45fd-a614-a40e3da5de90',
                'tag': '1',
                'flag1': '2',
                'flag2': '0',
                'flag3': '0',
                'minPlayers': '20',
                'desiredPlayers': '60',
                'maxPlayers': '30',
                'safeStartTime': '15',
                'missionTime': '75',
            },
            {
                'Mission Name': 'Bailey_TVT30_TestMission_v2',
                'Has `missionTestingInfo`': '1',
                'Has `missionType`': '1',
                'uuid': '',
                'tag': '2',
                'flag1': '4',
                'flag2': '2',
                'flag3': '0',
                'minPlayers': '25',
                'desiredPlayers': '80',
                'maxPlayers': '35',
                'safeStartTime': '10',
                'missionTime': '35',
            },
            {
                'Mission Name': 'Mom_Co25_TestNightMission_v1',
                'Has `missionTestingInfo`': '1',
                'Has `missionType`': '1',
                'uuid': '713cb2d8-2af1-4833-8521-1356423f4be4',
                'tag': '1',
                'flag1': '1',
                'flag2': '0',
                'flag3': '0',
                'minPlayers': '15',
                'desiredPlayers': '60',
                'maxPlayers': '25',
                'safeStartTime': '10',
                'missionTime': '90',
            },
        ],
    }


@pytest.fixture
def disk_metadata_1(metadata_1):
    with tempfile.NamedTemporaryFile(delete_on_close=False, mode='w', suffix='.csv') as tmp_file:
        writer = csv.DictWriter(tmp_file, fieldnames=metadata_1['fields'])
        writer.writeheader()
        for row in metadata_1['metadata']:
            writer.writerow(row)
        tmp_file.flush()
        tmp_file.close()
        yield tmp_file.name


@pytest.fixture
def arma_server(mocker):
    mocker.patch.object(
        Configuration,
        'load_toml',
        return_value=Configuration(
            {
                'server': {
                    'path': '/home/',
                },
                'session': {},
                'crons': {},
            }
        ),
    )
    return Server(Path(''), 'main')
