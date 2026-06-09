from uuid import UUID
from bw.session.api import SessionApi
from bw.auth.roles import Roles
import logging
from quart import Blueprint

from bw.web_utils import json_endpoint
from bw.response import JsonResponse, Ok
from bw.models.auth import User
from bw.auth.decorators import require_session, require_user_role


logger = logging.getLogger('bw.session')


def define(api: Blueprint, local: Blueprint, html: Blueprint):
    @api.post('/register')
    @json_endpoint
    @require_session
    @require_user_role(Roles.can_manage_session)
    async def register(session_user: User) -> JsonResponse:
        logger.info('New session registered')
        return await SessionApi().register()

    @api.post('/mission/finish')
    @json_endpoint
    @require_session
    @require_user_role(Roles.can_manage_session)
    async def finish_mission(
        session_user: User, session_id: UUID, mission_name_with_version: str, mission_map: str, player_count: int
    ) -> Ok:
        logger.info(f'Mission finished for session {session_id}')
        return await SessionApi().finish_mission(session_id, mission_name_with_version, mission_map, player_count)
