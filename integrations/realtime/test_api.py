# ruff: noqa: F811, F401

import queue
import pytest

from sqlalchemy import select

from bw.models.realtime import Event, QueuedEvent, PublishedEvent
from bw.error import EventNotRegistered
from bw.realtime.api import RealtimeApi
from bw.realtime.event import EventStore

from integrations.fixtures import state, session
from integrations.realtime.fixtures import (
    MockRealtimeEvent,
    uuid1,
    uuid2,
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
    RealtimeApi().push_event(state, mock_event_1)

    with state.Session.begin() as s:
        events = list(s.scalars(select(Event)))
        queued = list(s.scalars(select(QueuedEvent)))
        s.expunge_all()

    assert len(events) == 1
    assert len(queued) == 1
    assert queued[0].event == events[0].id
    assert events[0].event_id == mock_event_1.id


# ---------------------------------------------------------------------------
# RealtimeApi — publish_queued_events
# ---------------------------------------------------------------------------


def test__publish_queued_events__publishes_and_removes_queued_events(state, session, db_queued_event_1, db_queued_event_2):
    """Test that publish_queued_events creates PublishedEvent rows and removes QueuedEvent rows."""
    queued_events = [db_queued_event_1, db_queued_event_2]

    RealtimeApi().publish_queued_events(state, [queued_events[0]])

    with state.Session.begin() as s:
        remaining_queued = list(s.scalars(select(QueuedEvent)))
        published = list(s.scalars(select(PublishedEvent)))
        s.expunge_all()

    assert len(remaining_queued) == 1
    assert remaining_queued[0].event == db_queued_event_2.event

    assert len(published) == 1
    assert published[0].event == db_queued_event_1.event


def test__publish_queued_events__with_empty_list_changes_nothing(state, session, db_queued_event_1, db_queued_event_2):
    """Test that publish_queued_events with an empty iterable is a no-op."""
    RealtimeApi().publish_queued_events(state, [])

    with state.Session.begin() as s:
        queued = list(s.scalars(select(QueuedEvent)))
        published = list(s.scalars(select(PublishedEvent)))
        s.expunge_all()

    assert len(queued) == 2
    assert len(published) == 0
