from bw.web_event.base import global_registered_events
from bw.web_event.connection import EndEvent
import logging
from quart import Blueprint
from collections.abc import AsyncIterator

from bw.web_utils import json_endpoint, sse_endpoint
from bw.response import Created, DoesNotExist
from bw.auth.decorators import require_session, require_user_role
from bw.auth.roles import Roles
from bw.web_event import BaseEvent, StartEvent
from bw.state import State

logger = logging.getLogger('bw.realtime')


def define(api: Blueprint, local: Blueprint):
    @api.post('/')
    @json_endpoint
    @require_session
    @require_user_role(Roles.can_publish_realtime_events)
    async def push_event(event: str) -> Created | DoesNotExist:
        logger.info(f'Queueing event {event}')
        if event not in global_registered_events:
            return DoesNotExist()
        event_cls = global_registered_events[event]
        event_instance = event_cls()
        State.state.queue.on_event(event_instance)
        return Created()

    @api.get('/sse')
    @sse_endpoint
    async def subscribe() -> AsyncIterator[BaseEvent]:
        logger.info('Request subscribing to SSE stream')

        worker = State.state.queue.subscribe()
        yield StartEvent(worker_id=worker.id)
        with worker.process():
            while worker.alive:
                yield await worker.pop_event()
        yield EndEvent(worker_id=worker.id)
