import logging
from quart import Blueprint, request
from collections.abc import AsyncIterator

from bw.web_utils import json_endpoint, sse_endpoint
from bw.response import Created
from bw.auth.decorators import require_session, require_user_role
from bw.auth.roles import Roles
from bw.web_event.base import BaseEvent
from bw.state import State

logger = logging.getLogger('bw.realtime')


def define(api: Blueprint, local: Blueprint):
    @api.post('/')
    @json_endpoint
    @require_session
    @require_user_role(Roles.can_publish_realtime_events)
    async def push_event(event: BaseEvent) -> Created:
        State.state.queue.on_event(event)
        return Created()

    @api.get('/sse')
    @sse_endpoint  # ty: ignore [invalid-argument-type]
    async def subscribe() -> AsyncIterator[BaseEvent]:
        relevant_events = set(request.args.getlist('event'))
        relevant_namespaces = set(request.args.getlist('namespace'))

        worker = State.state.queue.subscribe()
        with worker.process():
            while True:
                event = await worker.pop_event()
                if not relevant_events and not relevant_namespaces:
                    yield event
                elif relevant_events and not relevant_namespaces and event.event in relevant_events:
                    yield event
                elif not relevant_events and relevant_namespaces and event.namespace in relevant_namespaces:
                    yield event
                elif (
                    relevant_events
                    and relevant_namespaces
                    and event.event in relevant_events
                    and event.namespace in relevant_namespaces
                ):
                    yield event
