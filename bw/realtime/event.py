from bw.error import EventNotRegistered
import datetime
from bw.web_event.base import global_registered_events
from sqlalchemy import select, or_, delete
import uuid
from collections.abc import Iterable
from bw.state import State
from bw.models.realtime import Event, QueuedEvent, PublishedEvent
from bw.web_event import BaseEvent
from bw.converters import make_json_safe


class EventStore:
    def create_event(self, state: State, event: BaseEvent) -> Event:
        event_model = Event(event=event.encoded_string(), event_id=event.id, data=make_json_safe(event.data()), retry=event.retry)
        with state.Session.begin() as session:
            session.add(event_model)
            session.flush()
            session.expunge(event_model)
        return event_model

    def queue_event(self, state: State, event: Event) -> QueuedEvent:
        queued_event = QueuedEvent(event=event.id)
        with state.Session.begin() as session:
            session.add(queued_event)
            session.flush()
            session.expunge(queued_event)
        return queued_event

    def publish_queued_event_bulk(self, state: State, queued_events: Iterable[QueuedEvent]) -> tuple[PublishedEvent, ...]:
        published_events = tuple([PublishedEvent(event=queued_event.event) for queued_event in queued_events])
        with state.Session.begin() as session:
            session.add_all(published_events)
            session.flush()
            session.expunge_all()
        return published_events

    def pop_queued_event_bulk(self, state: State, queued_events: Iterable[QueuedEvent]):
        with state.Session.begin() as session:
            query = delete(QueuedEvent).where(QueuedEvent.event.in_([event.event for event in queued_events]))
            session.execute(query)

    def web_event_from_model(self, event: Event) -> BaseEvent:
        if event.event not in global_registered_events:
            raise EventNotRegistered(event.event)

        kwargs = {}
        if event.event_id is not None:
            kwargs['id'] = event.event_id
        if event.data is not None:
            kwargs.update(event.data)

        event_cls = global_registered_events[event.event]
        return event_cls(**kwargs)

    def web_events_from_database(
        self,
        state: State,
        *,
        after: datetime.datetime | None = None,
        event_ids: Iterable[uuid.UUID] = (),
        encoded_event_names: Iterable[str] = (),
        event_namespaces: Iterable[str] = (),
    ) -> tuple[BaseEvent, ...]:
        with state.Session.begin() as session:
            query = select(Event)
            if event_ids or encoded_event_names or event_namespaces:
                query = query.where(
                    or_(
                        Event.event_id.in_(event_ids),
                        Event.event.in_(encoded_event_names),
                        or_(False, *[Event.event.like(f'{namespace}:%') for namespace in event_namespaces]),
                    )
                )
            if after:
                query = query.where(Event.creation_date >= after)

            found_events: tuple[Event, ...] = tuple(session.scalars(query).all())
            session.expunge_all()

        converted_events: list[BaseEvent] = []
        for event in found_events:
            converted_events.append(self.web_event_from_model(event))

        return tuple(converted_events)

    def queued_events_from_database(
        self,
        state: State,
        *,
        after: datetime.datetime | None = None,
        event_ids: Iterable[uuid.UUID] = (),
        encoded_event_names: Iterable[str] = (),
        event_namespaces: Iterable[str] = (),
    ) -> tuple[tuple[QueuedEvent, Event], ...]:
        with state.Session.begin() as session:
            query = select(QueuedEvent, Event).join_from(QueuedEvent, Event, QueuedEvent.event == Event.id)
            if event_ids or encoded_event_names or event_namespaces:
                query = query.where(
                    or_(
                        Event.event_id.in_(event_ids),
                        Event.event.in_(encoded_event_names),
                        or_(False, *[Event.event.like(f'{namespace}:%') for namespace in event_namespaces]),
                    )
                )
            if after:
                query = query.where(QueuedEvent.queued_time >= after)

            found_events: tuple[tuple[QueuedEvent, Event], ...] = tuple(session.execute(query).all())  # ty: ignore [invalid-assignment]
            session.expunge_all()

        return found_events
