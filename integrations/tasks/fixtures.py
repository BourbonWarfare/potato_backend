import datetime

import pytest
from sqlalchemy import func

from bw.converters import make_json_safe
from bw.models.tasks import Task, TaskState
from bw.tasks.kinds import Kind


class MockTask(Kind):
    def __init__(self, argument_1: str, argument_2: int):
        super().__init__(task_executor=self.run, argument_1=argument_1, argument_2=argument_2)

    def run(self, argument_1: str, argument_2: int):
        pass


class MockTaskWithReturn(Kind):
    def __init__(self):
        super().__init__(task_executor=self.run)

    def run(self):
        return {'result': 'my cool return'}


class MockTaskWithException(Kind):
    def __init__(self):
        super().__init__(task_executor=self.run)

    def run(self):
        raise RuntimeError('failure exception')


@pytest.fixture
def task_1():
    yield MockTask(argument_1='blah', argument_2=67)


@pytest.fixture
def task_2():
    yield MockTask(argument_1='second task', argument_2=22)


@pytest.fixture
def task_changing():
    def make():
        return MockTask(argument_1='blah', argument_2=67)

    return make


@pytest.fixture
def task_with_return():
    yield MockTaskWithReturn()


@pytest.fixture
def task_with_exception():
    yield MockTaskWithException()


@pytest.fixture
def db_task_with_return(state, task_with_return):
    task = Task(
        arguments=make_json_safe(task_with_return.to_dict()),
        uuid=task_with_return.uuid,
        time_until_stale=task_with_return.time_until_stale(),
    )
    with state.Session.begin() as session:
        session.add(task)
        session.flush()
        session.expunge(task)
    yield task


@pytest.fixture
def db_task_with_exception(state, task_with_exception):
    task = Task(
        arguments=make_json_safe(task_with_exception.to_dict()),
        uuid=task_with_exception.uuid,
        time_until_stale=task_with_exception.time_until_stale(),
    )
    with state.Session.begin() as session:
        session.add(task)
        session.flush()
        session.expunge(task)
    yield task


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
def db_stale_task_processing(state, task_changing):
    task_obj = task_changing()
    task = Task(
        arguments=make_json_safe(task_obj.to_dict()),
        uuid=task_obj.uuid,
        time_until_stale=task_obj.time_until_stale(),
        start_date=func.current_timestamp() - (task_obj.time_until_stale() + datetime.timedelta(seconds=1)),
        state=TaskState.PROCESSING,
    )
    with state.Session.begin() as session:
        session.add(task)
        session.flush()
        session.expunge(task)
    yield task


@pytest.fixture
def db_stale_task_queued(state, task_changing):
    task_obj = task_changing()
    task = Task(
        arguments=make_json_safe(task_obj.to_dict()),
        uuid=task_obj.uuid,
        time_until_stale=task_obj.time_until_stale(),
        start_date=func.current_timestamp() - (task_obj.time_until_stale() + datetime.timedelta(seconds=1)),
        state=TaskState.QUEUED,
    )
    with state.Session.begin() as session:
        session.add(task)
        session.flush()
        session.expunge(task)
    yield task


@pytest.fixture
def db_stale_task_stale(state, task_changing):
    task_obj = task_changing()
    task = Task(
        arguments=make_json_safe(task_obj.to_dict()),
        uuid=task_obj.uuid,
        time_until_stale=task_obj.time_until_stale(),
        start_date=func.current_timestamp() - (task_obj.time_until_stale() + datetime.timedelta(seconds=1)),
        state=TaskState.STALE,
    )
    with state.Session.begin() as session:
        session.add(task)
        session.flush()
        session.expunge(task)
    yield task


@pytest.fixture
def db_stale_task_failed(state, task_changing):
    task_obj = task_changing()
    task = Task(
        arguments=make_json_safe(task_obj.to_dict()),
        uuid=task_obj.uuid,
        time_until_stale=task_obj.time_until_stale(),
        start_date=func.current_timestamp() - (task_obj.time_until_stale() + datetime.timedelta(seconds=1)),
        state=TaskState.FAILED,
    )
    with state.Session.begin() as session:
        session.add(task)
        session.flush()
        session.expunge(task)
    yield task


@pytest.fixture
def db_task_processing(state, task_changing):
    task_obj = task_changing()
    task = Task(
        arguments=make_json_safe(task_obj.to_dict()),
        uuid=task_obj.uuid,
        time_until_stale=task_obj.time_until_stale(),
        start_date=func.current_timestamp(),
        state=TaskState.PROCESSING,
    )
    with state.Session.begin() as session:
        session.add(task)
        session.flush()
        session.expunge(task)
    yield task


@pytest.fixture
def db_task_success(state, task_changing):
    task_obj = task_changing()
    task = Task(
        arguments=make_json_safe(task_obj.to_dict()),
        uuid=task_obj.uuid,
        time_until_stale=task_obj.time_until_stale(),
        start_date=func.current_timestamp(),
        state=TaskState.COMPLETE,
    )
    with state.Session.begin() as session:
        session.add(task)
        session.flush()
        session.expunge(task)
    yield task


@pytest.fixture
def db_task_failure(state, task_changing):
    task_obj = task_changing()
    task = Task(
        arguments=make_json_safe(task_obj.to_dict()),
        uuid=task_obj.uuid,
        time_until_stale=task_obj.time_until_stale(),
        start_date=func.current_timestamp(),
        state=TaskState.FAILED,
    )
    with state.Session.begin() as session:
        session.add(task)
        session.flush()
        session.expunge(task)
    yield task


@pytest.fixture
def db_task_stale(state, task_changing):
    task_obj = task_changing()
    task = Task(
        arguments=make_json_safe(task_obj.to_dict()),
        uuid=task_obj.uuid,
        time_until_stale=task_obj.time_until_stale(),
        start_date=func.current_timestamp(),
        state=TaskState.STALE,
    )
    with state.Session.begin() as session:
        session.add(task)
        session.flush()
        session.expunge(task)
    yield task
