from bw.session.orbat import Orbat
from uuid import UUID
from bw.session.api import SessionApi
from bw.auth.roles import Roles
import logging
from quart import Blueprint
from dacite import from_dict

from bw.web_utils import json_endpoint, url_endpoint
from bw.response import JsonResponse, Ok
from bw.models.auth import User
from bw.auth.decorators import require_session, require_user_role


logger = logging.getLogger('bw.session')


def define(api: Blueprint):
    @api.post('/register')
    @url_endpoint
    @require_session
    @require_user_role(Roles.can_manage_session)
    async def register(session_user: User) -> JsonResponse:
        logger.info('New session registered')
        return await SessionApi().register()

    @api.post('/finish')
    @json_endpoint
    @require_session
    @require_user_role(Roles.can_manage_session)
    async def finish(session_user: User, session_id: UUID) -> JsonResponse:
        logger.info('Finishing session')
        return await SessionApi().finish(session_id)

    @api.get('/current')
    @url_endpoint
    @require_session
    @require_user_role(Roles.can_manage_session)
    async def current_session(session_user: User) -> JsonResponse:
        logger.info('Getting latest session')
        return await SessionApi().get_latest_session()

    @api.post('/mission/finish')
    @json_endpoint
    @require_session
    @require_user_role(Roles.can_manage_session)
    async def finish_mission(
        session_user: User,
        session_id: UUID,
        mission_name_with_version: str,
        mission_map: str,
        starting_orbat: dict,
        final_orbat: dict,
    ) -> Ok:
        logger.info(f'Mission finished for session {session_id}')
        starting_orbat_casted = from_dict(data_class=Orbat, data=starting_orbat)
        final_orbat_casted = from_dict(data_class=Orbat, data=final_orbat)
        return await SessionApi().finish_mission(
            session_id, mission_name_with_version, mission_map, starting_orbat_casted, final_orbat_casted
        )

    @api.post('/mission/safeStart/disabled')
    @json_endpoint
    @require_session
    @require_user_role(Roles.can_manage_session)
    async def safe_start_disabled(
        session_user: User,
        session_id: UUID,
        mission_name_with_version: str,
        mission_map: str,
        orbat: dict,
    ) -> Ok:
        logger.info(f'Safe start ended for session {session_id}')
        orbat_casted = from_dict(data_class=Orbat, data=orbat)
        return await SessionApi().safe_start_ended(session_id, mission_name_with_version, mission_map, orbat_casted)
