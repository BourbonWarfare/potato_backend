# ruff: noqa: F811, F401

import pytest
import uuid

from sqlalchemy import insert

from bw.models.realtime import Event, QueuedEvent
from bw.web_event.base import BaseEvent
from bw.converters import make_json_safe

from bw.events import Broker
from bw.realtime.queue import Queue

from integrations.fixtures import state, session
from integrations.auth.fixtures import (
    db_user_1,
    db_session_1,
    db_expired_session_1,
    role_2,
)


# ---------------------------------------------------------------------------
# Test event class — defined at module level so the metaclass registers it
# once into global_registered_events for the entire test session.
# ---------------------------------------------------------------------------


class MockRealtimeEvent(BaseEvent, event='test_event', namespace='test'):
    """Minimal concrete BaseEvent used across realtime integration tests."""

    def __init__(self, id: uuid.UUID = uuid.uuid4(), message: str = 'hello'):
        self.id = id
        self.message = message
        super().__init__()

    def data(self) -> dict:
        return {'message': self.message}


class MockDifferentNamespaceEvent(BaseEvent, event='test_event', namespace='test2'):
    """Minimal concrete BaseEvent used across realtime integration tests."""

    def __init__(self, id: uuid.UUID, message: str = 'hello'):
        self.id = id
        self.message = message
        super().__init__()

    def data(self) -> dict:
        return {'message': self.message}


class MockDifferentEventEvent(BaseEvent, event='test_event2', namespace='test'):
    """Minimal concrete BaseEvent used across realtime integration tests."""

    def __init__(self, id: uuid.UUID, message: str = 'hello'):
        self.id = id
        self.message = message
        super().__init__()

    def data(self) -> dict:
        return {'message': self.message}


# ---------------------------------------------------------------------------
# Session-scoped: immutable data
# ---------------------------------------------------------------------------


@pytest.fixture(scope='session')
def mock_event_message_1() -> str:
    return 'hello'


@pytest.fixture(scope='session')
def mock_event_message_2() -> str:
    return 'world'


@pytest.fixture(scope='session')
def uuid1() -> uuid.UUID:
    yield uuid.uuid4()


@pytest.fixture(scope='session')
def uuid2() -> uuid.UUID:
    yield uuid.uuid4()


@pytest.fixture(scope='session')
def uuid3() -> uuid.UUID:
    yield uuid.uuid4()


@pytest.fixture(scope='session')
def uuid4() -> uuid.UUID:
    yield uuid.uuid4()


@pytest.fixture(scope='session')
def mock_event_1(mock_event_message_1, uuid1) -> MockRealtimeEvent:
    return MockRealtimeEvent(id=uuid1, message=mock_event_message_1)


@pytest.fixture(scope='session')
def mock_event_2(mock_event_message_2, uuid2) -> MockRealtimeEvent:
    return MockRealtimeEvent(id=uuid2, message=mock_event_message_2)


@pytest.fixture(scope='session')
def mock_event_different_namespace(mock_event_message_1, uuid3) -> MockDifferentNamespaceEvent:
    return MockDifferentNamespaceEvent(id=uuid3, message=mock_event_message_1)


@pytest.fixture(scope='session')
def mock_event_different_event(mock_event_message_1, uuid4) -> MockDifferentEventEvent:
    return MockDifferentEventEvent(id=uuid4, message=mock_event_message_1)


@pytest.fixture(scope='session')
def unregistered_event_string() -> str:
    """An encoded event string that has deliberately never been registered."""
    return ':totally_unknown_event'


# ---------------------------------------------------------------------------
# Session-scoped: endpoint URLs
# ---------------------------------------------------------------------------


@pytest.fixture(scope='session')
def endpoint_api_url() -> str:
    return '/api'


@pytest.fixture(scope='session')
def endpoint_api_v1_url(endpoint_api_url) -> str:
    return f'{endpoint_api_url}/v1'


@pytest.fixture(scope='session')
def endpoint_realtime_url(endpoint_api_v1_url) -> str:
    return f'{endpoint_api_v1_url}/realtime'


@pytest.fixture(scope='session')
def endpoint_realtime_push_url(endpoint_realtime_url) -> str:
    return f'{endpoint_realtime_url}/'


@pytest.fixture(scope='session')
def endpoint_realtime_sse_url(endpoint_realtime_url) -> str:
    return f'{endpoint_realtime_url}/sse'


# ---------------------------------------------------------------------------
# Function-scoped: database objects
# ---------------------------------------------------------------------------


@pytest.fixture(scope='function')
def db_event_1(state, session, mock_event_1):
    """Persists mock_event_1 as an Event row and yields the detached model."""
    event_model = Event(
        event=mock_event_1.encoded_string(),
        event_id=mock_event_1.id,
        data=make_json_safe(mock_event_1.data()),
        retry=mock_event_1.retry,
    )
    with state.Session.begin() as s:
        s.add(event_model)
        s.flush()
        s.expunge(event_model)
    yield event_model


@pytest.fixture(scope='function')
def db_event_2(state, session, mock_event_2):
    """Persists mock_event_2 as an Event row and yields the detached model."""
    event_model = Event(
        event=mock_event_2.encoded_string(),
        event_id=mock_event_2.id,
        data=make_json_safe(mock_event_2.data()),
        retry=mock_event_2.retry,
    )
    with state.Session.begin() as s:
        s.add(event_model)
        s.flush()
        s.expunge(event_model)
    yield event_model


@pytest.fixture(scope='function')
def db_event_different_namespace(state, session, mock_event_different_namespace):
    """Persists mock_event_different_namespace as an Event row and yields the detached model."""
    event_model = Event(
        event=mock_event_different_namespace.encoded_string(),
        event_id=mock_event_different_namespace.id,
        data=make_json_safe(mock_event_different_namespace.data()),
        retry=mock_event_different_namespace.retry,
    )
    with state.Session.begin() as s:
        s.add(event_model)
        s.flush()
        s.expunge(event_model)
    yield event_model


@pytest.fixture(scope='function')
def db_event_different_event(state, session, mock_event_different_event):
    """Persists mock_event_different_event as an Event row and yields the detached model."""
    event_model = Event(
        event=mock_event_different_event.encoded_string(),
        event_id=mock_event_different_event.id,
        data=make_json_safe(mock_event_different_event.data()),
        retry=mock_event_different_event.retry,
    )
    with state.Session.begin() as s:
        s.add(event_model)
        s.flush()
        s.expunge(event_model)
    yield event_model


@pytest.fixture(scope='function')
def db_queued_event_1(state, session, db_event_1):
    """Queues db_event_1 and yields the detached QueuedEvent row."""
    queued = QueuedEvent(event=db_event_1.id)
    with state.Session.begin() as s:
        s.add(queued)
        s.flush()
        s.expunge(queued)
    yield queued


@pytest.fixture(scope='function')
def db_queued_event_different_namespace(state, session, db_event_different_namespace):
    """Queues db_event_1 and yields the detached QueuedEvent row."""
    queued = QueuedEvent(event=db_event_different_namespace.id)
    with state.Session.begin() as s:
        s.add(queued)
        s.flush()
        s.expunge(queued)
    yield queued


@pytest.fixture(scope='function')
def db_queued_event_different_event(state, session, db_event_different_event):
    """Queues db_event_1 and yields the detached QueuedEvent row."""
    queued = QueuedEvent(event=db_event_different_event.id)
    with state.Session.begin() as s:
        s.add(queued)
        s.flush()
        s.expunge(queued)
    yield queued


@pytest.fixture(scope='session')
def mock_broker() -> Broker:
    """Isolated Broker instance for queue tests — avoids polluting State.broker."""
    return Broker()


@pytest.fixture(scope='function')
def mock_queue(mock_broker) -> Queue:
    """Queue wired to mock_broker with zero delay for fast test iteration."""
    return Queue(mock_broker, delay=0)


@pytest.fixture(scope='function')
def db_queued_event_2(state, session, db_event_2):
    """Queues db_event_2 and yields the detached QueuedEvent row."""
    queued = QueuedEvent(event=db_event_2.id)
    with state.Session.begin() as s:
        s.add(queued)
        s.flush()
        s.expunge(queued)
    yield queued
