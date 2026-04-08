import asyncio
import logging
from dataclasses import dataclass
from contextlib import contextmanager
from bw.events import Broker
from bw.web_event.base import BaseEvent


logger = logging.getLogger('bw.realtime')


@dataclass
class Worker:
    messages: list[BaseEvent]
    alive: bool

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

    def on_event(self, event: BaseEvent):
        from bw.state import State
        from bw.realtime.api import RealtimeApi

        RealtimeApi().push_event(State.state, event)

    def subscribe(self) -> Worker:
        worker = Worker(messages=[], alive=True)
        self.queues.append(worker)
        return worker

    async def process_event_queue(self):
        from bw.state import State
        from bw.realtime.api import RealtimeApi
        from bw.realtime.event import EventStore

        logger.debug('start')
        while not self.dead:
            await asyncio.sleep(self.delay)
            logger.debug('tick')

            self.queues = [worker for worker in self.queues if worker.alive]
            logger.debug(f'{len(self.queues)} queues attached')

            queued_events = []
            for queued_event, event in EventStore().queued_events_from_database(State.state):
                web_event = EventStore().web_event_from_model(event)
                for queue in self.queues:
                    queue.messages.append(web_event)

                queued_events.append(queued_event)

            logger.debug(f'{len(queued_events)} queued events to publish')
            RealtimeApi().publish_queued_events(State.state, queued_events)
        logger.debug(f'end. dead? {self.dead}')
