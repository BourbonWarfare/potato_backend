import logging
from quart import Blueprint
from collections.abc import AsyncIterator

from bw.web_utils import json_endpoint, sse_endpoint
from bw.auth.decorators import require_session, require_user_role
from bw.auth.roles import Roles
from bw.web_event.base import BaseEvent

logger = logging.getLogger('bw.realtime')


def define(api: Blueprint, local: Blueprint):
    @api.post('/')
    @json_endpoint
    @require_session
    @require_user_role(Roles.can_publish_realtime_events)
    async def push_event(event: BaseEvent):
        raise NotImplementedError()

    @api.get('/sse')
    @sse_endpoint
    async def subscribe() -> AsyncIterator[BaseEvent]:
        raise NotImplementedError()
