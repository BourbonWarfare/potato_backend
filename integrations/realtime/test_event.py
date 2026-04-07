# ruff: noqa: F811, F401
"""
Tests for EventStore methods not covered by test_realtime_api.py.

test_realtime_api.py covers:
  create_event, queue_event, publish_queued_event_bulk, pop_queued_event_bulk,
  web_event_from_model, web_events_from_database

This file covers:
  queued_events_from_database (all variants)
"""

import datetime

import pytest

from sqlalchemy import select

from bw.error import EventNotRegistered
from bw.realtime.api import RealtimeApi

from bw.models.realtime import Event, QueuedEvent, PublishedEvent
from bw.realtime.event import EventStore

from integrations.fixtures import state, session
from integrations.realtime.fixtures import (
    MockRealtimeEvent,
    uuid1,
    uuid2,
    uuid3,
    uuid4,
    mock_event_1,
    mock_event_2,
    mock_event_different_event,
    mock_event_different_namespace,
    mock_event_message_1,
    mock_event_message_2,
    db_event_1,
    db_event_2,
    db_event_different_event,
    db_event_different_namespace,
    db_queued_event_1,
    db_queued_event_different_namespace,
    db_queued_event_different_event,
    db_queued_event_2,
    unregistered_event_string,
)


# ---------------------------------------------------------------------------
# EventStore — create_event
# ---------------------------------------------------------------------------


def test__create_event__persists_event_to_database(state, session, mock_event_1):
    """Test that create_event writes an Event row with the correct fields."""
    result = EventStore().create_event(state, mock_event_1)

    with state.Session.begin() as s:
        row = s.scalar(select(Event).where(Event.id == result.id))
        s.expunge_all()

    assert row is not None
    assert row.event == mock_event_1.encoded_string()
    assert row.data == mock_event_1.data()
    assert row.event_id == mock_event_1.id


def test__create_event__returns_detached_event_model(state, session, mock_event_1):
    """Test that create_event returns the persisted Event model outside the session."""
    result = EventStore().create_event(state, mock_event_1)

    assert isinstance(result, Event)
    assert result.id is not None


# ---------------------------------------------------------------------------
# EventStore — queue_event
# ---------------------------------------------------------------------------


def test__queue_event__persists_queued_event_to_database(state, session, db_event_1):
    """Test that queue_event writes a QueuedEvent row linked to the given event."""
    queued = EventStore().queue_event(state, db_event_1)

    with state.Session.begin() as s:
        row = s.scalar(select(QueuedEvent).where(QueuedEvent.event == db_event_1.id))
        s.expunge_all()

    assert row is not None
    assert row.event == queued.event


def test__queue_event__returns_detached_queued_event_model(state, session, db_event_1):
    """Test that queue_event returns the detached QueuedEvent model."""
    queued = EventStore().queue_event(state, db_event_1)

    assert isinstance(queued, QueuedEvent)


# ---------------------------------------------------------------------------
# EventStore — publish_queued_event_bulk
# ---------------------------------------------------------------------------


def test__publish_queued_event_bulk__creates_published_event_rows(state, session, db_queued_event_1, db_queued_event_2):
    """Test that publish_queued_event_bulk inserts a PublishedEvent for each queued event."""
    queued_events = [db_queued_event_1, db_queued_event_2]

    published = EventStore().publish_queued_event_bulk(state, queued_events)

    with state.Session.begin() as s:
        rows = list(s.scalars(select(PublishedEvent)))
        s.expunge_all()

    published_event_ids = {p.event for p in published}
    stored_event_ids = {r.event for r in rows}
    assert published_event_ids == stored_event_ids


def test__publish_queued_event_bulk__returns_published_event_models(state, session, db_queued_event_1):
    """Test that publish_queued_event_bulk returns a tuple of PublishedEvent instances."""
    published = EventStore().publish_queued_event_bulk(state, [db_queued_event_1])

    assert len(published) == 1
    assert isinstance(published[0], PublishedEvent)


# ---------------------------------------------------------------------------
# EventStore — pop_queued_event_bulk
# ---------------------------------------------------------------------------


def test__pop_queued_event_bulk__removes_queued_event_rows(state, session, db_queued_event_1, db_queued_event_2):
    """Test that pop_queued_event_bulk deletes the given QueuedEvent rows."""
    queued_events = [db_queued_event_1, db_queued_event_2]

    EventStore().pop_queued_event_bulk(state, queued_events)

    with state.Session.begin() as s:
        remaining = list(s.scalars(select(QueuedEvent)))
        s.expunge_all()

    assert len(remaining) == 0


def test__pop_queued_event_bulk__leaves_unrelated_queued_events_intact(state, session, db_queued_event_1, db_queued_event_2):
    """Test that pop_queued_event_bulk only removes the specified rows."""
    EventStore().pop_queued_event_bulk(state, [db_queued_event_1])

    with state.Session.begin() as s:
        remaining = list(s.scalars(select(QueuedEvent)))
        s.expunge_all()

    assert len(remaining) == 1
    assert remaining[0].event == db_queued_event_2.event


# ---------------------------------------------------------------------------
# EventStore — web_event_from_model
# ---------------------------------------------------------------------------


def test__web_event_from_model__reconstructs_correct_event_type(state, session, db_event_1, mock_event_message_1):
    """Test that web_event_from_model returns the correct BaseEvent subclass."""
    result = EventStore().web_event_from_model(db_event_1)

    assert isinstance(result, MockRealtimeEvent)
    assert result.data()['message'] == mock_event_message_1


def test__web_event_from_model__raises_when_event_not_registered(state, session, db_event_1, unregistered_event_string):
    """Test that web_event_from_model raises EventNotRegistered for unknown event strings."""
    db_event_1.event = unregistered_event_string

    with pytest.raises(EventNotRegistered):
        EventStore().web_event_from_model(db_event_1)


# ---------------------------------------------------------------------------
# EventStore — web_events_from_database
# ---------------------------------------------------------------------------


def test__web_events_from_database__returns_all_events_when_no_filters(state, session, db_event_1, db_event_2):
    """Test that web_events_from_database returns every stored event with no filters."""
    results = EventStore().web_events_from_database(state)

    assert len(results) == 2


def test__web_events_from_database__filters_by_encoded_event_name(
    state, session, db_event_1, db_event_different_event, mock_event_1
):
    """Test that web_events_from_database returns only events matching the given encoded name."""
    results = EventStore().web_events_from_database(state, encoded_event_names=[mock_event_1.encoded_string()])

    assert len(results) == 1
    assert results[0].encoded_string() == db_event_1.event


def test__web_events_from_database__returns_empty_tuple_when_no_matches(state, session, db_event_1):
    """Test that web_events_from_database returns an empty tuple when nothing matches the filter."""
    results = EventStore().web_events_from_database(state, encoded_event_names=[':no_such_event'])

    assert results == ()


def test__web_events_from_database__filters_by_namespace(state, session, db_event_1, db_event_different_namespace):
    """Test that web_events_from_database returns events whose encoded string matches the namespace prefix."""
    results = EventStore().web_events_from_database(state, event_namespaces=['test'])

    assert len(results) == 1
    assert results[0].encoded_string() == db_event_1.event


# ---------------------------------------------------------------------------
# EventStore — queued_events_from_database
# ---------------------------------------------------------------------------


def test__queued_events_from_database__returns_all_when_no_filters(state, session, db_queued_event_1, db_queued_event_2):
    """Test that queued_events_from_database returns every queued event when called with no filters."""
    # Not yet reviewed
    results = EventStore().queued_events_from_database(state)

    assert len(results) == 2


def test__queued_events_from_database__returns_empty_tuple_when_queue_is_empty(state, session):
    """Test that queued_events_from_database returns an empty tuple when nothing is queued."""
    # Not yet reviewed
    results = EventStore().queued_events_from_database(state)

    assert results == ()


def test__queued_events_from_database__filters_by_encoded_event_name(
    state, session, uuid1, uuid2, mock_event_1, db_queued_event_1, db_queued_event_2
):
    """Test that queued_events_from_database returns only entries whose Event matches the given encoded name."""
    # Not yet reviewed
    results = EventStore().queued_events_from_database(state, encoded_event_names=[mock_event_1.encoded_string()])

    # Both db_event_1 and db_event_2 share the same MockRealtimeEvent encoded string
    assert len(results) == 2


def test__queued_events_from_database__filters_by_event_id(
    state, session, db_event_1, db_queued_event_1, db_queued_event_different_event
):
    """Test that queued_events_from_database returns only the entry whose Event.event_id matches."""
    # Not yet reviewed
    results = EventStore().queued_events_from_database(state, event_ids=[db_event_1.event_id])

    assert len(results) == 1
    queued, event = results[0]
    assert event.id == db_event_1.id


def test__queued_events_from_database__filters_by_namespace(
    state, session, db_queued_event_1, db_queued_event_different_event, db_queued_event_different_namespace
):
    """Test that queued_events_from_database returns entries whose Event matches the namespace prefix."""
    results = EventStore().queued_events_from_database(state, event_namespaces=['test'])

    assert len(results) == 2
    assert results[0][0].event == db_queued_event_1.event
    assert results[1][0].event == db_queued_event_different_event.event


def test__queued_events_from_database__namespace_filter_excludes_non_matching(state, session, db_queued_event_1):
    """Test that queued_events_from_database returns nothing when the namespace does not match any events."""
    results = EventStore().queued_events_from_database(state, event_namespaces=['no_such_namespace'])

    assert results == ()


def test__queued_events_from_database__filters_by_after_datetime(state, session, uuid1, db_queued_event_1, db_queued_event_2):
    """Test that queued_events_from_database excludes entries queued before the given datetime."""
    future = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)

    results = EventStore().queued_events_from_database(
        state,
        encoded_event_names=[MockRealtimeEvent(id=uuid1).encoded_string()],
        after=future,
    )

    assert results == ()


def test__queued_events_from_database__each_result_is_queued_event_and_event_pair(state, session, db_event_1, db_queued_event_1):
    """Test that each entry returned by queued_events_from_database is a (QueuedEvent, Event) pair."""
    # Not yet reviewed
    results = EventStore().queued_events_from_database(state)

    assert len(results) == 1
    queued, event = results[0]
    assert isinstance(queued, QueuedEvent)
    assert isinstance(event, Event)
    assert queued.event == event.id
