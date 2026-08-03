import datetime

import pytest
from sqlalchemy import func

from bw.converters import make_json_safe
from bw.models.tasks import Task, TaskState
from bw.tasks.kinds import Kind


class MockTask(Kind):
    def __init__(self, argument_1: str, argument_2: int):
        super().__init__(task_executor=self.run, argument_1=argument_1, argument_2=argument_2)

        self.has_run: bool = False
        self.argument_1: str | None = None
        self.argument_2: int | None = None

    def run(self, argument_1: str, argument_2: int):
        self.has_run = True
        self.argument_1 = argument_1
        self.argument_2 = argument_2


@pytest.fixture
def task_1():
    return MockTask(argument_1='blah', argument_2=67)


@pytest.fixture
def task_2():
    return MockTask(argument_1='second task', argument_2=22)


@pytest.fixture
def db_task_1(state, task_1):
    task = Task(arguments=make_json_safe(task_1.to_dict()), uuid=task_1.uuid, time_until_stale=task_1.time_until_stale())
    with state.Session.begin() as session:
        session.add(task)
        session.flush()
        session.expunge(task)
    yield task


@pytest.fixture
def db_task_2(state, task_2):
    task = Task(arguments=make_json_safe(task_2.to_dict()), uuid=task_2.uuid, time_until_stale=task_2.time_until_stale())
    with state.Session.begin() as session:
        session.add(task)
        session.flush()
        session.expunge(task)
    yield task


@pytest.fixture
def db_stale_task_processing(state, task_1):
    task = Task(
        arguments=make_json_safe(task_1.to_dict()),
        uuid=task_1.uuid,
        time_until_stale=task_1.time_until_stale(),
        start_date=func.current_timestamp() - (task_1.time_until_stale() + datetime.timedelta(seconds=1)),
        state=TaskState.PROCESSING,
    )
    with state.Session.begin() as session:
        session.add(task)
        session.flush()
        session.expunge(task)
    yield task


@pytest.fixture
def db_stale_task_queued(state, task_1):
    task = Task(
        arguments=make_json_safe(task_1.to_dict()),
        uuid=task_1.uuid,
        time_until_stale=task_1.time_until_stale(),
        start_date=func.current_timestamp() - (task_1.time_until_stale() + datetime.timedelta(seconds=1)),
        state=TaskState.QUEUED,
    )
    with state.Session.begin() as session:
        session.add(task)
        session.flush()
        session.expunge(task)
    yield task


@pytest.fixture
def db_stale_task_stale(state, task_1):
    task = Task(
        arguments=make_json_safe(task_1.to_dict()),
        uuid=task_1.uuid,
        time_until_stale=task_1.time_until_stale(),
        start_date=func.current_timestamp() - (task_1.time_until_stale() + datetime.timedelta(seconds=1)),
        state=TaskState.STALE,
    )
    with state.Session.begin() as session:
        session.add(task)
        session.flush()
        session.expunge(task)
    yield task


@pytest.fixture
def db_stale_task_failed(state, task_1):
    task = Task(
        arguments=make_json_safe(task_1.to_dict()),
        uuid=task_1.uuid,
        time_until_stale=task_1.time_until_stale(),
        start_date=func.current_timestamp() - (task_1.time_until_stale() + datetime.timedelta(seconds=1)),
        state=TaskState.FAILED,
    )
    with state.Session.begin() as session:
        session.add(task)
        session.flush()
        session.expunge(task)
    yield task
