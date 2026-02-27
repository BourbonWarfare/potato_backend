# ruff: noqa: F811, F401

import pytest
from sqlalchemy import select

from bw.error import CouldNotCreateMissionType, NoMissionTypeWithName, CouldNotCreateIteration, MissionDoesNotExist
from bw.models.missions import Mission, MissionType, Iteration
from bw.missions.missions import MissionStore, MissionTypeStore
from integrations.missions.fixtures import (
    state,
    session,
    db_mission_type_1,
    db_mission_type_2,
    db_user_1,
    db_mission_1,
    db_iteration_1,
    db_iteration_2,
    db_mission_1_1,
    db_mission_1_2,
)


def test__mission_type_store__create_mission_type__can_create_mission_type(state, session):
    mission_type = MissionTypeStore().create_mission_type(state, 'mission', 5, 1)
    assert mission_type.name == 'mission'
    assert mission_type.signoffs_required == 5
    assert mission_type.numeric_tag == 1

    with state.Session.begin() as session:
        query = select(MissionType).where(MissionType.id == mission_type.id)
        row = session.execute(query).first()
        assert row is not None


def test__mission_type_store__create_mission_type__cant_create_duplicate(state, session):
    MissionTypeStore().create_mission_type(state, 'mission', 5, 1)
    with pytest.raises(CouldNotCreateMissionType):
        MissionTypeStore().create_mission_type(state, 'mission', 5, 1)


def test__mission_type_store__update_mission_type__can_update_mission(state, session, db_mission_type_1, db_mission_type_2):
    MissionTypeStore().update_mission_type(state, name=db_mission_type_1.name, new_signoff_requirement=50)
    with state.Session.begin() as session:
        query = select(MissionType).where(MissionType.id == db_mission_type_1.id)
        row = session.execute(query).first()
        assert row is not None
        assert row[0].signoffs_required == 50
        assert row[0].numeric_tag == db_mission_type_1.numeric_tag

    MissionTypeStore().update_mission_type(state, name=db_mission_type_2.name, new_tag=2)
    with state.Session.begin() as session:
        query = select(MissionType).where(MissionType.id == db_mission_type_2.id)
        row = session.execute(query).first()
        assert row is not None
        assert row[0].signoffs_required == db_mission_type_2.signoffs_required
        assert row[0].numeric_tag == 2


def test__mission_type_store__update_mission_type__updating_none_raises(state, session):
    with pytest.raises(NoMissionTypeWithName):
        MissionTypeStore().update_mission_type(state, name='')


def test__mission_type_store__delete_mission_type__can_delete(state, session, db_mission_type_1):
    MissionTypeStore().delete_mission_type(state, name=db_mission_type_1.name)
    with state.Session.begin() as session:
        query = select(MissionType).where(MissionType.id == db_mission_type_1.id)
        row = session.execute(query).first()
        assert row is None


def test__mission_type_store__delete_mission_type__nothing_deleting_null(state, session, db_mission_type_1):
    MissionTypeStore().delete_mission_type(state, name='foboar')
    with state.Session.begin() as session:
        query = select(MissionType).where(MissionType.id == db_mission_type_1.id)
        row = session.execute(query).first()
        assert row is not None


def test__mission_type_store__mission_type_from_name__can_retrieve(state, session, db_mission_type_1):
    mission_type = MissionTypeStore().mission_type_from_name(state, name=db_mission_type_1.name)
    assert mission_type.id == db_mission_type_1.id
    assert mission_type.name == db_mission_type_1.name
    assert mission_type.signoffs_required == db_mission_type_1.signoffs_required
    assert mission_type.numeric_tag == db_mission_type_1.numeric_tag


def test__mission_type_store__mission_type_from_name__retrieve_none_raises(state, session):
    with pytest.raises(NoMissionTypeWithName):
        MissionTypeStore().mission_type_from_name(state, name='')


def test__mission_store__create_mission__can_create(state, session, db_user_1, db_mission_type_1):
    mission = MissionStore().create_mission(
        state,
        server='main',
        creator=db_user_1,
        author='AuthorName',
        title='Test Mission',
        type=db_mission_type_1,
        flags={'foo': 'bar'},
    )
    assert mission.server == 'main'
    assert mission.author == db_user_1.id
    assert mission.author_name == 'AuthorName'
    assert mission.title == 'Test Mission'
    assert mission.mission_type == db_mission_type_1.id
    assert mission.special_flags == {'foo': 'bar'}
    with state.Session.begin() as session:
        query = select(Mission).where(Mission.id == mission.id)
        row = session.execute(query).first()
        assert row is not None


def test__mission_store__add_iteration__first_iteration_is_one(state, session, db_mission_1):
    iteration = MissionStore().add_iteration(
        state,
        mission=db_mission_1,
        mission_file='mission_v1.pbo',
        min_players=5,
        desired_players=10,
        max_players=15,
        safe_start_length=10,
        mission_length=30,
        bwmf_version='1.0.0',
        changelog={},
    )
    assert iteration.mission_id == db_mission_1.id
    assert iteration.file_name == 'mission_v1.pbo'
    assert iteration.min_player_count == 5
    assert iteration.max_player_count == 15
    assert iteration.desired_player_count == 10
    assert iteration.bwmf_version == '1.0.0'
    assert iteration.changelog == {}
    assert iteration.iteration == 1
    with state.Session.begin() as session:
        query = select(Iteration).where(Iteration.id == iteration.id)
        row = session.execute(query).first()
        assert row is not None


def test__mission_store__add_iteration__increments_iteration(state, session, db_mission_1, db_iteration_1):
    iteration = MissionStore().add_iteration(
        state,
        mission=db_mission_1,
        mission_file='mission_v2.pbo',
        min_players=6,
        desired_players=12,
        max_players=18,
        safe_start_length=10,
        mission_length=30,
        bwmf_version='1.1.0',
        changelog={},
    )
    assert iteration.iteration == db_iteration_1.iteration + 1
    assert iteration.file_name == 'mission_v2.pbo'
    with state.Session.begin() as session:
        query = select(Iteration).where(Iteration.id == iteration.id)
        row = session.execute(query).first()
        assert row is not None


def test__mission_store__all_mission_iterations__returns_all(state, session, db_mission_1, db_iteration_1, db_iteration_2):
    iterations = MissionStore().all_mission_iterations(state, db_mission_1)
    ids = [it.id for it in iterations]
    assert db_iteration_1.id in ids
    assert db_iteration_2.id in ids


def test__mission_store__add_iteration__invalid_mission_raises(state, session):
    with pytest.raises(MissionDoesNotExist):
        MissionStore().add_iteration(
            state,
            mission=Mission(id=1, author=1, author_name='me', title='some mission', mission_type=1, special_flags={}),
            mission_file='bad.pbo',
            min_players=1,
            desired_players=1,
            max_players=1,
            safe_start_length=10,
            mission_length=30,
            bwmf_version='0.0.1',
            changelog={},
        )


def test__mission_store__create_mission__invalid_args_raises(state, session, db_user_1, db_mission_type_1):
    with pytest.raises(Exception):
        MissionStore().create_mission(state, creator=db_user_1, author=None, title=None, type=db_mission_type_1, flags=None)


def test__mission_store__get_missions_by_author__returns_missions(
    state, session, db_user_1, db_mission_1, db_mission_1_1, db_mission_1_2
):
    missions = MissionStore().get_missions_by_author(state, author='me')
    assert len(missions) == 3
    assert missions[0].id == db_mission_1.id
    assert missions[1].id == db_mission_1_1.id
    assert missions[2].id == db_mission_1_2.id


def test__mission_store__get_missions_by_author_with_title__returns_missions_only_with_title(
    state, session, db_user_1, db_mission_1, db_mission_1_1, db_mission_1_2
):
    missions = MissionStore().get_existing_missions_by_author_with_title(state, author='me', title=db_mission_1.title)
    assert len(missions) == 2
    assert missions[0].id == db_mission_1.id
    assert missions[1].id == db_mission_1_2.id
