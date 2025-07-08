import logging
import uuid

from bw.server import app
from bw.web_utils import json_api, url_api
from bw.response import JsonResponse, WebResponse
from bw.models.auth import User
from bw.auth.decorators import require_session, require_local, require_user_role
from bw.auth.permissions import Permissions
from bw.auth.roles import Roles
from bw.auth.api import AuthApi
from bw.state import State


logger = logging.getLogger('quart.app')


@app.post('/api/v1/users/login/bot')
@json_api
async def login_bot(bot_token: str) -> JsonResponse:
    logger.info('Creating new session (bot)')
    return AuthApi().login_with_bot(state=State.state, bot_token=bot_token)


@app.post('/api/v1/users/create_role')
@json_api
@require_session
async def create_role(session_user: User, role_name: str, **kwargs) -> JsonResponse:
    logger.info('Creating new role')
    role = Roles.from_keys(**kwargs)
    return AuthApi().create_role(State.state, role_name=role_name, roles=role)


@app.post('/api/v1/users/add_role')
@json_api
@require_session
async def assign_role(session_user: User, role_name: str, user_uuid: str) -> WebResponse:
    logger.info(f'Assigning {role_name} to user {user_uuid}')
    return AuthApi().assign_role(State.state, role_name=role_name, user_uuid=uuid.UUID(hex=user_uuid))


@app.post('/api/v1/users/groups/create_permission')
@json_api
@require_session
@require_user_role(Roles.can_create_group)
async def create_group_permission(session_user: User, permission_name: str, **kwargs) -> JsonResponse:
    logger.info(f"Creating new group permission '{permission_name}'")
    permission = Permissions.from_keys(default_if_key_not_present=False, **kwargs)
    return AuthApi().create_group_permission(State.state, permission_name=permission_name, permissions=permission)


@app.post('/api/v1/users/groups/create_group')
@json_api
@require_session
@require_user_role(Roles.can_create_group)
async def create_group(session_user: User, group_name: str, permissions: str) -> JsonResponse:
    logger.info(f'Creating new group {group_name} with permissions {permissions}')
    return AuthApi().create_group(state=State.state, group_name=group_name, permission_group=permissions)


@app.post('/api/v1/users/join_group')
@json_api
@require_session
async def join_group(session_user: User, group_name: str) -> WebResponse:
    logger.info(f'User {session_user.id} is joining group {group_name}')
    return AuthApi().join_group(state=State.state, user=session_user, group_name=group_name)


@app.post('/api/v1/users/leave_group')
@json_api
@require_session
async def leave_group(session_user: User, group_name: str) -> WebResponse:
    logger.info(f'User {session_user.id} is leaving group {group_name}')
    return AuthApi().leave_group(state=State.state, user=session_user, group_name=group_name)


# required to bootstrap server
@app.post('/api/local/users/create_bot')
@url_api
@require_local
async def local_create_bot() -> JsonResponse:
    logger.info('Creating new bot user (Local)')
    return AuthApi().create_new_user_bot(state=State.state)


@app.post('/api/local/users/create_role')
@json_api
@require_local
@require_session
async def local_create_role(session_user: User, role_name: str, **kwargs) -> JsonResponse:
    logger.info('Creating new role (Local)')
    role = Roles.from_keys(**kwargs)
    return AuthApi().create_role(State.state, role_name=role_name, roles=role)


@app.post('/api/local/users/assign_role')
@json_api
@require_local
@require_session
async def local_assign_role(session_user: User, role_name: str, user_uuid: str) -> WebResponse:
    logger.info(f'Assigning {role_name} to user {user_uuid} (Local)')
    return AuthApi().assign_role(State.state, role_name=role_name, user_uuid=uuid.UUID(hex=user_uuid))
