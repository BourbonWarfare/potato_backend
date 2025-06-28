# ruff: noqa: F811, F401

import pytest

from sqlalchemy import insert

from bw.models.auth import User
from bw.models.missions import Mission, MissionType, Iteration, Review, TestResult
from bw.missions.test_status import TestStatus
from integrations.fixtures import session, state


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
def db_mission_type_1(state, session):
    with state.Session.begin() as session:
        mission_type = MissionType(name='TVT', signoffs_required=1, tag_map='tvt')
        session.add(mission_type)
        session.flush()
        session.expunge(mission_type)
    yield mission_type


@pytest.fixture(scope='function')
def db_mission_type_2(state, session):
    with state.Session.begin() as session:
        mission_type = MissionType(name='LONG COOP', signoffs_required=2, tag_map='lc')
        session.add(mission_type)
        session.flush()
        session.expunge(mission_type)
    yield mission_type


@pytest.fixture(scope='function')
def db_mission_1(state, session, db_user_1, db_mission_type_1):
    with state.Session.begin() as session:
        mission = Mission(
            id=1,
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
