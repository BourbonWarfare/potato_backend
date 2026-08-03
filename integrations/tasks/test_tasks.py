# ruff: noqa: F811, F401

import pytest
from sqlalchemy import select

from bw.error import NoTasksAvailable
from bw.models.tasks import Task, TaskState
from bw.tasks.tasks import TasksStore
from integrations.tasks.fixtures import (
    db_stale_task_failed,
    db_stale_task_processing,
    db_stale_task_queued,
    db_stale_task_stale,
    db_task_1,
    db_task_2,
    task_1,
    task_2,
)


def test__enqueue_task__happy_path(session, state, task_1):
    task_uuid = TasksStore().enqueue_task(state, task_1)

    assert task_uuid == task_1.uuid
    with state.Session.begin() as db_session:
        query = select(Task).where(Task.uuid == task_uuid)
        task = db_session.execute(query).scalar_one()
        db_session.expunge_all()

    assert task.uuid == task_1.uuid
    assert task.arguments == task_1.to_dict()


def test__pop_task_to_process__happy_path_gets_task(session, state, task_1, db_task_1):
    popped_task = TasksStore().pop_task_to_process(state)

    assert popped_task.uuid == task_1.uuid
    assert popped_task.arguments == task_1.arguments


def test__pop_task_to_process__happy_path_updates_state(session, state, task_1, db_task_1):
    TasksStore().pop_task_to_process(state)

    with state.Session.begin() as db_session:
        query = select(Task).where(Task.uuid == task_1.uuid)
        task = db_session.execute(query).scalar_one()
        db_session.expunge_all()

    assert task.state == TaskState.PROCESSING


def test__pop_task_to_process__happy_path_updates_start_date(session, state, task_1, db_task_1):
    TasksStore().pop_task_to_process(state)

    with state.Session.begin() as db_session:
        query = select(Task).where(Task.uuid == task_1.uuid)
        task = db_session.execute(query).scalar_one()
        db_session.expunge_all()

    assert task.start_date is not None


def test__pop_task_to_process__no_task_raises(session, state):
    with pytest.raises(NoTasksAvailable):
        TasksStore().pop_task_to_process(state)


def test__pop_task_to_process__row_lock_returns_only_one_task(session, state, task_1, db_task_1):
    with state.Session.begin() as lock_session:
        lock_session.execute(select(Task).where(Task.uuid == db_task_1.uuid).with_for_update())

        # Because the row is locked and pop_task_to_process skips locked rows,
        # it should act as if no task is available.
        with pytest.raises(NoTasksAvailable):
            TasksStore().pop_task_to_process(state)


def test__pop_task_to_process__row_lock_returns_next_task(session, state, task_2, db_task_1, db_task_2):
    with state.Session.begin() as lock_session:
        lock_session.execute(select(Task).where(Task.uuid == db_task_1.uuid).with_for_update())

        # Since db_task_1 is locked, pop_task_to_process skips it and pops db_task_2
        popped_task = TasksStore().pop_task_to_process(state)
        assert popped_task.uuid == db_task_2.uuid


def test__fail_task__happy_path_updates_state_to_default(session, state, task_1, db_task_1):
    TasksStore().fail_task(state, task_1, 'Failure reason')

    with state.Session.begin() as db_session:
        query = select(Task).where(Task.uuid == task_1.uuid)
        task = db_session.execute(query).scalar_one()
        db_session.expunge_all()

    assert task.state == TaskState.FAILED


def test__fail_task__happy_path_updates_only_specific_task(session, state, task_1, db_task_1, db_task_2):
    TasksStore().fail_task(state, task_1, 'Failure reason')

    with state.Session.begin() as db_session:
        t1 = db_session.execute(select(Task).where(Task.uuid == task_1.uuid)).scalar_one()
        t2 = db_session.execute(select(Task).where(Task.uuid == db_task_2.uuid)).scalar_one()
        db_session.expunge_all()

    assert t1.state == TaskState.FAILED
    assert t2.state == TaskState.QUEUED


def test__fail_task__happy_path_updates_state_to_specific(session, state, task_1, db_task_1):
    TasksStore().fail_task(state, task_1, 'Stale task', task_state=TaskState.STALE)

    with state.Session.begin() as db_session:
        query = select(Task).where(Task.uuid == task_1.uuid)
        task = db_session.execute(query).scalar_one()
        db_session.expunge_all()

    assert task.state == TaskState.STALE


def test__fail_task__happy_path_updates_result(session, state, task_1, db_task_1):
    reason = 'An error occurred'
    TasksStore().fail_task(state, task_1, reason)

    with state.Session.begin() as db_session:
        query = select(Task).where(Task.uuid == task_1.uuid)
        task = db_session.execute(query).scalar_one()
        db_session.expunge_all()

    assert task.result == {'reason': reason}


def test__fail_task__no_db_task_does_nothing(session, state, task_1):
    TasksStore().fail_task(state, task_1, 'Error')

    with state.Session.begin() as db_session:
        query = select(Task).where(Task.uuid == task_1.uuid)
        task = db_session.execute(query).scalar_one_or_none()
        db_session.expunge_all()

    assert task is None


def test__finish_task__happy_path_updates_state_to_default(session, state, task_1, db_task_1):
    TasksStore().finish_task(state, task_1, {'success': True})

    with state.Session.begin() as db_session:
        query = select(Task).where(Task.uuid == task_1.uuid)
        task = db_session.execute(query).scalar_one()
        db_session.expunge_all()

    assert task.state == TaskState.COMPLETE


def test__finish_task__happy_path_updates_only_specific_task(session, state, task_1, db_task_1, db_task_2):
    TasksStore().finish_task(state, task_1, {'success': True})

    with state.Session.begin() as db_session:
        t1 = db_session.execute(select(Task).where(Task.uuid == task_1.uuid)).scalar_one()
        t2 = db_session.execute(select(Task).where(Task.uuid == db_task_2.uuid)).scalar_one()
        db_session.expunge_all()

    assert t1.state == TaskState.COMPLETE
    assert t2.state == TaskState.QUEUED


def test__finish_task__happy_path_updates_result(session, state, task_1, db_task_1):
    result = {'processed': 100}
    TasksStore().finish_task(state, task_1, result)

    with state.Session.begin() as db_session:
        query = select(Task).where(Task.uuid == task_1.uuid)
        task = db_session.execute(query).scalar_one()
        db_session.expunge_all()

    assert task.result == result


def test__finish_task__no_db_task_does_nothing(session, state, task_1):
    TasksStore().finish_task(state, task_1, {'processed': 100})

    with state.Session.begin() as db_session:
        query = select(Task).where(Task.uuid == task_1.uuid)
        task = db_session.execute(query).scalar_one_or_none()
        db_session.expunge_all()

    assert task is None


def test__get_stale_tasks__gets_no_stale_tasks(session, state, task_1, db_task_1):
    stale_tasks = TasksStore().get_stale_tasks(state)
    assert stale_tasks == []


def test__get_stale_tasks__gets_only_stale_tasks(session, state, task_1, db_stale_task_processing, db_task_2):
    stale_tasks = TasksStore().get_stale_tasks(state)
    assert len(stale_tasks) == 1
    assert stale_tasks[0].uuid == db_stale_task_processing.uuid


def test__get_stale_tasks__gets_stale_task_processing(session, state, task_1, db_stale_task_processing):
    stale_tasks = TasksStore().get_stale_tasks(state)
    assert len(stale_tasks) == 1
    assert stale_tasks[0].uuid == db_stale_task_processing.uuid


def test__get_stale_tasks__gets_stale_task_queued(session, state, task_1, db_stale_task_queued):
    stale_tasks = TasksStore().get_stale_tasks(state)
    assert len(stale_tasks) == 1
    assert stale_tasks[0].uuid == db_stale_task_queued.uuid


def test__get_stale_tasks__doesnt_get_stale_stale(session, state, task_1, db_stale_task_stale):
    stale_tasks = TasksStore().get_stale_tasks(state)
    assert stale_tasks == []


def test__get_stale_tasks__doesnt_get_stale_failed(session, state, task_1, db_stale_task_failed):
    stale_tasks = TasksStore().get_stale_tasks(state)
    assert stale_tasks == []
