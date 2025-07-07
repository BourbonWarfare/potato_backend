import logging

from bw.server import app
from bw.web_utils import json_api
from bw.response import JsonResponse
from bw.models.auth import User
from bw.auth.decorators import require_session, require_group_permission
from bw.auth.permissions import Permissions
from bw.missions.api import MissionsApi


logger = logging.getLogger('quart.app')


@app.post('/api/v1/missions/upload/<string:location>')
@json_api
@require_session
@require_group_permission(Permissions.can_upload_mission)
async def upload(location: str, session_user: User, pbo_path: str, changelog: dict[str, str]) -> JsonResponse:
    logger.info(f'User {session_user.id} is uploading mission from {pbo_path} to {location} with changelog: {changelog}')
    await MissionsApi().upload_mission_metadata(stored_pbo_path=pbo_path)
    return JsonResponse({})
