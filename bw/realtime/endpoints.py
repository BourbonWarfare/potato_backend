from bw.web_event.connection import EndEvent
import logging
from quart import Blueprint, request
from collections.abc import AsyncIterator

from bw.web_utils import json_endpoint, sse_endpoint
from bw.response import Created
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
    async def push_event(event: BaseEvent) -> Created:
        logger.info(f'Queueing event {event.encoded_string()}')
        State.state.queue.on_event(event)
        return Created()

    @api.get('/sse')
    @sse_endpoint
    async def subscribe() -> AsyncIterator[BaseEvent]:
        logger.info('Request subscribing to SSE stream')
        print(1)
        relevant_events = set(request.args.getlist('event'))
        print(2)
        relevant_namespaces = set(request.args.getlist('namespace'))

        print(3)
        worker = State.state.queue.subscribe()
        print(4)
        yield StartEvent(worker_id=worker.id)
        print(5)
        with worker.process():
            print(6)
            while worker.alive:
                print(7)
                event = await worker.pop_event()
                should_yield = (
                    (not relevant_events and not relevant_namespaces)
                    or (relevant_events and not relevant_namespaces and event.event in relevant_events)
                    or (not relevant_events and relevant_namespaces and event.namespace in relevant_namespaces)
                    or (
                        relevant_events
                        and relevant_namespaces
                        and event.event in relevant_events
                        and event.namespace in relevant_namespaces
                    )
                )
                if should_yield:
                    yield event
        print(8)
        yield EndEvent(worker_id=worker.id)
