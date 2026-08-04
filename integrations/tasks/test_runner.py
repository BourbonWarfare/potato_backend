# ruff: noqa: F811, F401

from unittest.mock import ANY, patch

from sqlalchemy import select

from bw.models.tasks import Task, TaskState
from bw.tasks.runner import Runner
from integrations.tasks.fixtures import (
    MockTask,
    db_stale_task_processing,
    db_task_1,
    db_task_2,
    db_task_failure,
    db_task_processing,
    db_task_stale,
    db_task_success,
    db_task_with_exception,
    db_task_with_return,
    task_1,
    task_2,
    task_changing,
    task_with_exception,
    task_with_return,
)


def test__process_task__existing_task_runs(session, state, task_1, db_task_1):
    with patch.object(MockTask, 'run', return_value=None) as mock_run:
        Runner().process_task()
        mock_run.assert_called_once_with(argument_1='blah', argument_2=67)


def test__process_task__task_failure_sets_failure(session, state, db_task_with_exception):
    Runner().process_task()

    with state.Session.begin() as db_session:
        task = db_session.execute(select(Task).where(Task.uuid == db_task_with_exception.uuid)).scalar_one()
        db_session.expunge_all()

    assert task.state == TaskState.FAILED
    assert task.result == {'reason': 'failure exception'}


def test__process_task__task_success_sets_success(session, state, db_task_1):
    Runner().process_task()

    with state.Session.begin() as db_session:
        task = db_session.execute(select(Task).where(Task.uuid == db_task_1.uuid)).scalar_one()
        db_session.expunge_all()

    assert task.state == TaskState.COMPLETE


def test__process_task__task_success_sets_result(session, state, db_task_with_return):
    Runner().process_task()

    with state.Session.begin() as db_session:
        task = db_session.execute(select(Task).where(Task.uuid == db_task_with_return.uuid)).scalar_one()
        db_session.expunge_all()

    assert task.state == TaskState.COMPLETE
    assert task.result == {'result': 'my cool return'}


def test__process_task__no_task_noop(session, state):
    assert not Runner().process_task()


def test__process_task__only_runs_queued(session, state, db_task_success, db_task_failure, db_task_stale, db_task_processing):
    Runner().process_task()

    with state.Session.begin() as db_session:
        t_success = db_session.execute(select(Task).where(Task.uuid == db_task_success.uuid)).scalar_one()
        t_failure = db_session.execute(select(Task).where(Task.uuid == db_task_failure.uuid)).scalar_one()
        t_stale = db_session.execute(select(Task).where(Task.uuid == db_task_stale.uuid)).scalar_one()
        t_proc = db_session.execute(select(Task).where(Task.uuid == db_task_processing.uuid)).scalar_one()
        db_session.expunge_all()

    assert t_success.state == TaskState.COMPLETE
    assert t_failure.state == TaskState.FAILED
    assert t_stale.state == TaskState.STALE
    assert t_proc.state == TaskState.PROCESSING


def test__process_task__all_tasks_run(session, state, task_1, task_2, db_task_1, db_task_2):
    runner = Runner()
    runner.process_task()
    runner.process_task()

    with state.Session.begin() as db_session:
        t1 = db_session.execute(select(Task).where(Task.uuid == db_task_1.uuid)).scalar_one()
        t2 = db_session.execute(select(Task).where(Task.uuid == db_task_2.uuid)).scalar_one()
        db_session.expunge_all()

    assert t1.state == TaskState.COMPLETE
    assert t2.state == TaskState.COMPLETE


def test__reap_stale_tasks__updates_stale_tasks(session, state, db_task_1, db_stale_task_processing):
    Runner().reap_stale_tasks()

    with state.Session.begin() as db_session:
        t1 = db_session.execute(select(Task).where(Task.uuid == db_task_1.uuid)).scalar_one()
        t_stale = db_session.execute(select(Task).where(Task.uuid == db_stale_task_processing.uuid)).scalar_one()
        db_session.expunge_all()

    assert t1.state == TaskState.QUEUED
    assert t_stale.state == TaskState.STALE
    assert t_stale.result == {'reason': 'task has become stale'}
