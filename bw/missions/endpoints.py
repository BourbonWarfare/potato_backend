import logging
from quart import render_template_string

from bw.server import app
from bw.web_utils import json_api, html_api
from bw.response import JsonResponse
from bw.models.auth import User
from bw.auth.decorators import require_session, require_group_permission
from bw.auth.permissions import Permissions
from bw.missions.api import MissionsApi
from bw.events import ServerEvent


logger = logging.getLogger('bw.missions')


@app.post('/api/v1/missions/upload/<string:location>')
@json_api
@require_session
@require_group_permission(Permissions.can_upload_mission)
async def upload(location: str, session_user: User, pbo_path: str, changelog: dict[str, str]) -> JsonResponse:
    logger.info(f'User {session_user.id} is uploading mission from {pbo_path} to {location} with changelog: {changelog}')
    await MissionsApi().upload_mission_metadata(stored_pbo_path=pbo_path)
    return JsonResponse({})


@app.get('/')
@html_api(template_path='home.html', title='Bourbon Warfare')
async def html_home(html: str) -> str:
    return await render_template_string(
        html,
    )


@app.get('/missions/list')
@html_api(template_path='missions/home.html', title='BW Mission List', expire_event=ServerEvent.MISSION_UPLOADED)
async def html_missions_list(html: str) -> str:
    metadata = await MissionsApi().get_stored_metadata()
    return await render_template_string(
        html,
        missions=metadata.contained_json.get('metadata', []),
    )
