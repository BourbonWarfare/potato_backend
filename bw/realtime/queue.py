import asyncio
import logging
import uuid
from dataclasses import dataclass
from contextlib import contextmanager
from bw.events import Broker
import bw.web_event  # noqa: F401
from bw.web_event.base import BaseEvent


logger = logging.getLogger('bw.realtime')


@dataclass
class Worker:
    messages: list[BaseEvent]
    alive: bool
    uuid: uuid.UUID = uuid.uuid4()

    @contextmanager
    def process(self):
        self.alive = True
        try:
            yield
        finally:
            self.alive = False

    async def pop_event(self) -> BaseEvent:
        while not self.messages:
            await asyncio.sleep(0.25)
        return self.messages.pop(0)


class Queue:
    dead: bool
    delay: float
    queues: list[Worker]

    def __init__(self, broker: Broker, delay: float = 5.0):
        self.dead = False
        self.delay = delay
        self.queues = []
        broker.subscribe_all(self.on_event)

    def stop(self):
        self.dead = True
        for worker in self.queues:
            worker.alive = False

    def on_event(self, event: BaseEvent):
        from bw.state import State
        from bw.realtime.api import RealtimeApi

        RealtimeApi().push_event(State.state, event)

    def subscribe(self) -> Worker:
        worker = Worker(messages=[], alive=not self.dead)
        self.queues.append(worker)
        return worker

    async def process_event_queue(self):
        from bw.state import State
        from bw.realtime.api import RealtimeApi
        from bw.realtime.event import EventStore

        while not self.dead:
            await asyncio.sleep(self.delay)

            self.queues = [worker for worker in self.queues if worker.alive]

            queued_events = []
            for queued_event, event in EventStore().queued_events_from_database(State.state):
                web_event = EventStore().web_event_from_model(event)
                for queue in self.queues:
                    queue.messages.append(web_event)

                queued_events.append(queued_event)

            RealtimeApi().publish_queued_events(State.state, queued_events)
