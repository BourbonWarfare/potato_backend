import logging
from quart import render_template_string

from bw.server import app
from bw.web_utils import json_endpoint, html_endpoint
from bw.response import JsonResponse
from bw.models.auth import User
from bw.auth.decorators import require_session, require_group_permission
from bw.auth.permissions import Permissions
from bw.missions.api import MissionsApi
from bw.events import ServerEvent


logger = logging.getLogger('bw.missions')


@app.post('/api/v1/missions/upload/<string:location>')
@json_endpoint
@require_session
@require_group_permission(Permissions.can_upload_mission)
async def upload(location: str, session_user: User, pbo_path: str, changelog: dict[str, str]) -> JsonResponse:
    """
    ### Upload a mission to a specific location

    Uploads a mission from a PBO file to the specified location. The mission metadata is logged
    and the operation is tracked. Requires an active session and `can_upload_mission` permission.

    **Args:**
    - `location` (`str`): The destination location for the mission upload (path parameter).
    - `session_user` (`User`): The authenticated user (automatically injected by `@require_session`).
    - `pbo_path` (`str`): The file path to the PBO file to upload.
    - `changelog` (`dict[str, str]`): A dictionary containing changelog entries for this upload.

    **Returns:**
    - `JsonResponse`:
      - **Success (200)**: `{}` (empty JSON object)
      - **Error (401)**: `{'status': 401, 'reason': 'Session is not valid'}`
      - **Error (403)**: `{'status': 403, 'reason': 'User does not have permission'}`
      - **Error (422)**: `{'status': 422, 'reason': 'mission does not have attached mission testing attributes'}`
      - **Error (500)**: Internal server error if mission loading fails

    **Example:**
    ```
    POST /api/v1/missions/upload/testing
    {
        "pbo_path": "/path/to/mission.pbo",
        "changelog": {
            "version": "1.0",
            "changes": "Initial release"
        }
    }
    ```
    """
    logger.info(f'User {session_user.id} is uploading mission from {pbo_path} to {location} with changelog: {changelog}')
    await MissionsApi().upload_mission_metadata(stored_pbo_path=pbo_path)
    return JsonResponse({})


@app.get('/')
@html_endpoint(template_path='home.html', title='Bourbon Warfare')
async def html_home(html: str) -> str:
    """
    ### Home page

    Renders the main home page of the Bourbon Warfare application.

    **Returns:**
    - `str`: HTML content of the home page.

    **Example:**
    ```
    GET /
    ```
    Returns the rendered HTML home page.
    """
    return await render_template_string(
        html,
    )


@app.get('/missions')
@html_endpoint(template_path='missions/home.html', title='BW Mission List', expire_event=ServerEvent.MISSION_UPLOADED)
async def html_missions_list(html: str) -> str:
    """
    ### Mission list page

    Renders the mission list page displaying all uploaded missions and their metadata.
    This page is automatically refreshed when new missions are uploaded (expire_event).

    **Args:**
    - `html` (`str`): The HTML template content (automatically injected by `@html_endpoint`).

    **Returns:**
    - `str`: HTML content of the mission list page with mission data.

    **Example:**
    ```
    GET /missions
    ```
    Returns the rendered HTML mission list page with all mission metadata.
    """
    metadata = await MissionsApi().get_stored_metadata()
    return await render_template_string(
        html,
        missions=metadata.contained_json.get('metadata', []),
    )
