# ruff: noqa: F811, F401

from cffi.pkgconfig import call
import asyncio

import pytest

from bw.realtime.queue import Queue, Worker
from bw.realtime.api import RealtimeApi

from integrations.fixtures import state, session
from integrations.realtime.fixtures import (
    MockRealtimeEvent,
    uuid1,
    uuid2,
    mock_broker,
    mock_queue,
    mock_event_1,
    mock_event_2,
    db_event_1,
    db_event_2,
    db_queued_event_1,
    db_queued_event_2,
    mock_event_message_1,
    mock_event_message_2,
)


# ---------------------------------------------------------------------------
# Worker — process (context manager)
# ---------------------------------------------------------------------------


def test__process__sets_alive_true_while_inside_context():
    """Test that Worker.alive is True for the duration of the process context."""
    worker = Worker(messages=[], alive=False)

    with worker.process():
        assert worker.alive is True


def test__process__sets_alive_false_after_context_exits():
    """Test that Worker.alive is False once the process context manager exits normally."""
    worker = Worker(messages=[], alive=False)

    with worker.process():
        pass

    assert worker.alive is False


def test__process__sets_alive_false_even_when_exception_raised():
    """Test that Worker.alive is False after the process context exits via an exception."""
    worker = Worker(messages=[], alive=False)

    with pytest.raises(RuntimeError):
        with worker.process():
            raise RuntimeError('unexpected error')

    assert worker.alive is False


# ---------------------------------------------------------------------------
# Worker — pop_event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test__pop_event__returns_first_message_immediately_when_available():
    """Test that pop_event returns the first message without waiting when messages is non-empty."""
    event = MockRealtimeEvent()
    worker = Worker(messages=[event], alive=True)

    result = await worker.pop_event()

    assert result is event


@pytest.mark.asyncio
async def test__pop_event__removes_returned_message_from_queue():
    """Test that pop_event removes the returned message from the worker's message list."""
    event = MockRealtimeEvent()
    worker = Worker(messages=[event], alive=True)

    await worker.pop_event()

    assert len(worker.messages) == 0


@pytest.mark.asyncio
async def test__pop_event__preserves_fifo_order(mock_event_1, mock_event_2):
    """Test that pop_event returns messages in the order they were added."""
    worker = Worker(messages=[mock_event_1, mock_event_2], alive=True)

    first = await worker.pop_event()
    second = await worker.pop_event()

    assert first is mock_event_1
    assert second is mock_event_2


@pytest.mark.asyncio
async def test__pop_event__waits_until_message_is_available(mocker):
    """Test that pop_event suspends until a message appears, then returns it."""
    worker = Worker(messages=[], alive=True)
    event = MockRealtimeEvent()

    sleep_call_count = 0
    original_sleep = asyncio.sleep

    async def inject_after_first_sleep(delay):
        nonlocal sleep_call_count
        sleep_call_count += 1
        await original_sleep(0)
        if sleep_call_count == 1:
            worker.messages.append(event)

    mocker.patch('bw.realtime.queue.asyncio.sleep', side_effect=inject_after_first_sleep)

    result = await worker.pop_event()

    assert result is event
    assert sleep_call_count >= 1


# ---------------------------------------------------------------------------
# Queue — subscribe
# ---------------------------------------------------------------------------


def test__subscribe__returns_worker_instance(mock_queue):
    """Test that Queue.subscribe returns a Worker."""
    worker = mock_queue.subscribe()

    assert isinstance(worker, Worker)


def test__subscribe__each_call_returns_a_distinct_worker(mock_queue):
    """Test that successive subscribe calls return different Worker instances."""
    worker_a = mock_queue.subscribe()
    worker_b = mock_queue.subscribe()

    assert worker_a is not worker_b


# ---------------------------------------------------------------------------
# Queue — process_event_queue
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test__process_event_queue__distributes_queued_events_to_active_workers(
    mocker, state, session, mock_queue, db_queued_event_1, db_queued_event_2
):
    """Test that process_event_queue pushes each queued event to every active worker."""
    worker = mock_queue.subscribe()

    call_count = 0

    async def sleep_then_cancel(delay):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()

    mocker.patch('bw.realtime.queue.asyncio.sleep', side_effect=sleep_then_cancel)
    mocker.patch.object(RealtimeApi, 'publish_queued_events')

    with worker.process():
        with pytest.raises(asyncio.CancelledError):
            await mock_queue.process_event_queue()

    assert len(worker.messages) == 2


@pytest.mark.asyncio
async def test__process_event_queue__skips_dead_workers(mocker, state, session, mock_queue, db_queued_event_1):
    """Test that process_event_queue does not deliver events to workers whose alive flag is False."""
    worker = mock_queue.subscribe()
    worker.alive = False

    call_count = 0

    async def sleep_once(delay):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()

    mocker.patch('bw.realtime.queue.asyncio.sleep', side_effect=sleep_once)
    mocker.patch.object(RealtimeApi, 'publish_queued_events')

    with pytest.raises(asyncio.CancelledError):
        await mock_queue.process_event_queue()

    assert len(worker.messages) == 0
