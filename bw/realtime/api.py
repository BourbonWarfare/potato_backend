from bw.models.realtime import QueuedEvent
from collections.abc import Iterable
from bw.realtime.event import EventStore
from bw.state import State
from bw.web_event.base import BaseEvent


class RealtimeApi:
    def push_event(self, state: State, event: BaseEvent):
        new_event = EventStore().create_event(state, event)
        EventStore().queue_event(state, new_event)

    def publish_queued_events(self, state: State, events: Iterable[QueuedEvent]):
        EventStore().publish_queued_event_bulk(state, events)
        EventStore().pop_queued_event_bulk(state, events)
