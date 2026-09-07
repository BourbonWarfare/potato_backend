import datetime
from heapq import heappush
from pathlib import Path

import pytest

from bw.cron.runner import Module, Runner, ScheduledCron
from bw.settings import TIMEZONE
from crons.cron import Cron


class TestCron(Cron):
    runs = 0
    callbacks = []  # noqa: RUF012

    @classmethod
    def cron_str(cls):
        return '* * * * *'

    def __init__(self, callback):
        type(self).callbacks.append(callback)

    def run(self):
        type(self).runs += 1

    async def async_run(self):
        pass

    async def request(self, session):
        pass


class HourlyCron(Cron):
    runs = 0

    @classmethod
    def cron_str(cls):
        return '0 * * * *'

    def __init__(self, callback):
        pass

    def run(self):
        type(self).runs += 1

    async def async_run(self):
        pass

    async def request(self, session):
        pass


@pytest.fixture(autouse=True)
def reset_test_crons():
    TestCron.runs = 0
    TestCron.callbacks = []
    HourlyCron.runs = 0


@pytest.fixture
def runner():
    runner = Runner.__new__(Runner)
    runner.crons_ = set()
    runner.loaded_crons_ = {}
    runner.cron_queue_ = []
    runner.last_schedule_print_ = datetime.datetime.fromtimestamp(
        0,
        tz=TIMEZONE,
    )
    return runner


@pytest.fixture
def now():
    return datetime.datetime.now(TIMEZONE).replace(
        second=0,
        microsecond=0,
    )


@pytest.fixture
def now_half():
    return datetime.datetime.now(TIMEZONE).replace(
        second=0,
        microsecond=500000,
    )


def make_scheduled_cron(
    cron_class,
    init_time,
    next_run,
    path='/crons/cron_test.py',
):
    cron = ScheduledCron(
        path=Path(path),
        cron_class=cron_class,
        init_time=init_time,
    )
    cron.next = lambda: next_run
    return cron


def test__scheduled_cron__next_returns_next_occurrence(now_half):
    cron = ScheduledCron(
        path=Path('/crons/cron_test.py'),
        cron_class=TestCron,
        init_time=now_half,
    )

    assert cron.next() > now_half


def test__runner__schedule_cron_schedules_cron_in_execution_order(
    runner,
    now,
):
    runner.schedule_cron(
        Path('/crons/hourly.py'),
        HourlyCron,
    )
    runner.schedule_cron(
        Path('/crons/minutely.py'),
        TestCron,
    )

    first = runner.cron_queue_[0]

    assert first.path == Path('/crons/minutely.py')


def test__runner__reschedule_schedules_next_occurrence(
    runner,
    now,
):
    scheduled = ScheduledCron(
        path=Path('/crons/cron_test.py'),
        cron_class=TestCron,
        init_time=now,
    )

    next_init_time = now + datetime.timedelta(minutes=1)

    runner.reschedule(scheduled, next_init_time)

    assert len(runner.cron_queue_) == 1
    assert runner.cron_queue_[0].path == scheduled.path
    assert runner.cron_queue_[0].cron_class is TestCron
    assert runner.cron_queue_[0].init_time == next_init_time


def test__runner__run_due_crons_runs_cron(
    runner,
    now,
):
    scheduled = make_scheduled_cron(
        TestCron,
        now,
        now,
    )
    runner.cron_queue_ = [scheduled]

    class AsyncRunner:
        def run(self, coroutine):
            coroutine.close()

    runner.run_due_crons(AsyncRunner(), now)

    assert TestCron.runs == 1


def test__runner__run_due_crons_does_not_run_future_cron(
    runner,
    now,
):
    scheduled = make_scheduled_cron(
        TestCron,
        now,
        now + datetime.timedelta(minutes=1),
    )
    runner.cron_queue_ = [scheduled]

    class AsyncRunner:
        def run(self, coroutine):
            coroutine.close()

    runner.run_due_crons(AsyncRunner(), now)

    assert TestCron.runs == 0


def test__runner__run_due_crons_runs_crons_in_chronological_order(
    runner,
    now,
):
    events = []

    class FirstCron(Cron):
        @classmethod
        def cron_str(cls):
            return '* * * * *'

        def __init__(self, callback):
            pass

        def run(self):
            events.append('first')

        async def async_run(self):
            pass

        async def request(self, session):
            pass

    class SecondCron(Cron):
        @classmethod
        def cron_str(cls):
            return '* * * * *'

        def __init__(self, callback):
            pass

        def run(self):
            events.append('second')

        async def async_run(self):
            pass

        async def request(self, session):
            pass

    first = make_scheduled_cron(
        FirstCron,
        now,
        now - datetime.timedelta(minutes=2),
        '/crons/first.py',
    )
    second = make_scheduled_cron(
        SecondCron,
        now,
        now - datetime.timedelta(minutes=1),
        '/crons/second.py',
    )

    runner.cron_queue_ = []
    heappush(runner.cron_queue_, second)
    heappush(runner.cron_queue_, first)

    class AsyncRunner:
        def run(self, coroutine):
            coroutine.close()

    runner.run_due_crons(AsyncRunner(), now)

    assert events == ['first', 'second']


def test__runner__run_due_crons_runs_cron_scheduled_exactly_now(
    runner,
    now,
):
    scheduled = make_scheduled_cron(
        TestCron,
        now,
        now,
    )
    runner.cron_queue_ = [scheduled]

    class AsyncRunner:
        def run(self, coroutine):
            coroutine.close()

    runner.run_due_crons(AsyncRunner(), now)

    assert TestCron.runs == 1


def test__runner__run_due_crons_reschedules_executed_cron(
    runner,
    now,
):
    scheduled = make_scheduled_cron(
        TestCron,
        now,
        now - datetime.timedelta(minutes=1),
    )
    runner.cron_queue_ = [scheduled]

    class AsyncRunner:
        def run(self, coroutine):
            coroutine.close()

    runner.run_due_crons(AsyncRunner(), now)

    assert len(runner.cron_queue_) == 1
    assert runner.cron_queue_[0].path == scheduled.path
    assert runner.cron_queue_[0].cron_class is TestCron
    assert runner.cron_queue_[0].init_time == now


def test__runner__run_due_crons_reschedules_cron_even_when_another_cron_is_later(
    runner,
    now,
):
    executed = make_scheduled_cron(
        TestCron,
        now,
        now - datetime.timedelta(minutes=1),
        '/crons/executed.py',
    )
    later = make_scheduled_cron(
        HourlyCron,
        now,
        now + datetime.timedelta(minutes=10),
        '/crons/later.py',
    )

    runner.cron_queue_ = [executed, later]

    class AsyncRunner:
        def run(self, coroutine):
            coroutine.close()

    runner.run_due_crons(AsyncRunner(), now)

    assert len(runner.cron_queue_) == 2

    scheduled_paths = {cron.path for cron in runner.cron_queue_}

    assert Path('/crons/executed.py') in scheduled_paths
    assert Path('/crons/later.py') in scheduled_paths


def test__runner__run_due_crons_reschedules_every_executed_cron(
    runner,
    now,
):
    first = make_scheduled_cron(
        TestCron,
        now,
        now - datetime.timedelta(minutes=2),
        '/crons/first.py',
    )
    second = make_scheduled_cron(
        HourlyCron,
        now,
        now - datetime.timedelta(minutes=1),
        '/crons/second.py',
    )

    runner.cron_queue_ = [first, second]

    class AsyncRunner:
        def run(self, coroutine):
            coroutine.close()

    runner.run_due_crons(AsyncRunner(), now)

    assert len(runner.cron_queue_) == 2
    assert {cron.path for cron in runner.cron_queue_} == {
        Path('/crons/first.py'),
        Path('/crons/second.py'),
    }


def test__runner__gather_crons_schedules_new_cron(
    runner,
    mocker,
    tmp_path,
):
    cron_file = tmp_path / 'cron_test.py'
    cron_file.write_text('')

    mocker.patch(
        'bw.cron.runner.ENVIRONMENT.cron_path',
        return_value=tmp_path,
    )
    mocker.patch.object(runner, 'write_schedules')

    runner.loaded_crons_ = {
        cron_file: Module(
            module=mocker.Mock(),
            last_modified=cron_file.stat().st_mtime,
            cron_class=TestCron,
        )
    }

    runner.gather_crons()

    assert cron_file in runner.crons_
    assert len(runner.cron_queue_) == 1
    assert runner.cron_queue_[0].path == cron_file


def test__runner__gather_crons_does_not_duplicate_existing_cron(
    runner,
    mocker,
    tmp_path,
):
    cron_file = tmp_path / 'cron_test.py'
    cron_file.write_text('')

    mocker.patch(
        'bw.cron.runner.ENVIRONMENT.cron_path',
        return_value=tmp_path,
    )
    mocker.patch.object(runner, 'write_schedules')

    runner.crons_ = {cron_file}
    runner.loaded_crons_ = {
        cron_file: Module(
            module=mocker.Mock(),
            last_modified=cron_file.stat().st_mtime,
            cron_class=TestCron,
        )
    }

    runner.gather_crons()

    assert runner.cron_queue_ == []


@pytest.mark.asyncio
async def test__runner__push_cron_run_event(
    runner,
    mocker,
):
    runner.push_event = mocker.AsyncMock()

    event = mocker.patch('bw.cron.runner.CronRun')
    event.return_value.encoded_string.return_value = 'cron-run'
    event.return_value.cron = 'cron_test'

    scheduled = ScheduledCron(
        path=Path('/crons/cron_test.py'),
        cron_class=TestCron,
        init_time=datetime.datetime.now(TIMEZONE),
    )

    await runner.push_cron_run_event(scheduled)

    event.assert_called_once_with(cron='cron_test')
    runner.push_event.assert_awaited_once_with(
        'cron-run',
        {'cron': 'cron_test'},
    )
