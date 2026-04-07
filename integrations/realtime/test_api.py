# ruff: noqa: F811, F401

import pytest

from sqlalchemy import select

from bw.models.realtime import Event, QueuedEvent, PublishedEvent
from bw.error import EventNotRegistered
from bw.realtime.api import RealtimeApi
from bw.realtime.event import EventStore

from integrations.fixtures import state, session
from integrations.realtime.fixtures import (
    MockRealtimeEvent,
    mock_event_1,
    mock_event_2,
    mock_event_message_1,
    mock_event_message_2,
    db_event_1,
    db_event_2,
    db_queued_event_1,
    db_queued_event_2,
    unregistered_event_string,
)


# ---------------------------------------------------------------------------
# RealtimeApi — push_event
# ---------------------------------------------------------------------------


def test__push_event__creates_event_and_queued_event_in_database(state, session, mock_event_1):
    """Test that push_event stores both an Event and a QueuedEvent row."""
    # Not yet reviewed
    RealtimeApi().push_event(state, mock_event_1)

    with state.Session.begin() as s:
        events = list(s.scalars(select(Event)))
        queued = list(s.scalars(select(QueuedEvent)))

    assert len(events) == 1
    assert len(queued) == 1
    assert queued[0].event == events[0].id


# ---------------------------------------------------------------------------
# RealtimeApi — publish_queued_events
# ---------------------------------------------------------------------------


def test__publish_queued_events__publishes_and_removes_queued_events(state, session, db_queued_event_1, db_queued_event_2):
    """Test that publish_queued_events creates PublishedEvent rows and removes QueuedEvent rows."""
    # Not yet reviewed
    queued_events = [db_queued_event_1, db_queued_event_2]

    RealtimeApi().publish_queued_events(state, queued_events)

    with state.Session.begin() as s:
        remaining_queued = list(s.scalars(select(QueuedEvent)))
        published = list(s.scalars(select(PublishedEvent)))

    assert len(remaining_queued) == 0
    assert len(published) == 2


def test__publish_queued_events__with_empty_list_changes_nothing(state, session):
    """Test that publish_queued_events with an empty iterable is a no-op."""
    # Not yet reviewed
    RealtimeApi().publish_queued_events(state, [])

    with state.Session.begin() as s:
        published = list(s.scalars(select(PublishedEvent)))

    assert len(published) == 0
