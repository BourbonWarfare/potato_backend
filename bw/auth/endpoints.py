import logging
import uuid

from bw.server import app
from bw.web_utils import json_endpoint, url_endpoint
from bw.response import JsonResponse, WebResponse
from bw.models.auth import User
from bw.auth.decorators import require_session, require_local, require_user_role
from bw.auth.permissions import Permissions
from bw.auth.roles import Roles
from bw.auth.api import AuthApi
from bw.state import State


logger = logging.getLogger('bw.auth')


@app.post('/api/v1/users/auth/bot')
@json_endpoint
async def login_bot(bot_token: str) -> JsonResponse:
    """
    ### Log in with bot token

    Authenticates a bot user and creates a new API session.

    **Args:**
    - `bot_token` (`str`): The bot token for authentication.

    **Returns:**
    - `JsonResponse`:
      - **Success (200)**: `{'session_token': str, 'expire_time': str}`
      - **Error (404)**: `{'status': 404, 'reason': 'User does not exist'}`

    **Example:**
    ```
    POST /api/v1/users/auth/bot
    {
        "bot_token": "your_bot_token_here"
    }
    ```
    """
    logger.info('Creating new session (bot)')
    return AuthApi().login_with_bot(state=State.state, bot_token=bot_token)


@app.post('/api/v1/users/create_role')
@json_endpoint
@require_session
async def create_role(session_user: User, role_name: str, **kwargs) -> JsonResponse:
    """
    ### Create a new role

    Creates a new role with the specified name and role permissions. Requires an active session.

    **Args:**
    - `session_user` (`User`): The authenticated user (automatically injected by `@require_session`).
    - `role_name` (`str`): The name of the role to create.
    - `**kwargs`: Role permissions as key-value pairs (e.g., `can_create_group=True`).

    **Returns:**
    - `JsonResponse`:
      - **Success (201)**: `{'name': str, 'status': 201}`
      - **Error (400)**: `{'status': 400, 'reason': 'Creation of role "{role_name}" failed.'}`
      - **Error (403)**: `{'status': 403, 'reason': 'Session is not valid'}`

    **Example:**
    ```
    POST /api/v1/users/create_role
    {
        "role_name": "moderator",
        "can_create_group": true,
        "can_manage_users": false
    }
    ```
    """
    logger.info('Creating new role')
    role = Roles.from_keys(**kwargs)
    return AuthApi().create_role(State.state, role_name=role_name, roles=role)


@app.post('/api/v1/users/add_role')
@json_endpoint
@require_session
async def assign_role(session_user: User, role_name: str, user_uuid: str) -> WebResponse:
    """
    ### Assign a role to a user

    Assigns the specified role to the user with the given UUID. Requires an active session.

    **Args:**
    - `session_user` (`User`): The authenticated user (automatically injected by `@require_session`).
    - `role_name` (`str`): The name of the role to assign.
    - `user_uuid` (`str`): The UUID of the user to assign the role to.

    **Returns:**
    - `WebResponse`:
      - **Success (200)**: Empty response body
      - **Error (403)**: `{'status': 403, 'reason': 'Session is not valid'}`
      - **Error (404)**: `{'status': 404, 'reason': 'User does not exist'}` or `{'status': 404, 'reason': 'Role does not exist'}`

    **Example:**
    ```
    POST /api/v1/users/add_role
    {
        "role_name": "moderator",
        "user_uuid": "12345678-1234-5678-9012-123456789012"
    }
    ```
    """
    logger.info(f'Assigning {role_name} to user {user_uuid}')
    return AuthApi().assign_role(State.state, role_name=role_name, user_uuid=uuid.UUID(hex=user_uuid))


@app.post('/api/v1/users/groups/create_permission')
@json_endpoint
@require_session
@require_user_role(Roles.can_create_group)
async def create_group_permission(session_user: User, permission_name: str, **kwargs) -> JsonResponse:
    """
    ### Create a new group permission

    Creates a new group permission with the specified name and permission settings.
    Requires an active session and the `can_create_group` role.

    **Args:**
    - `session_user` (`User`): The authenticated user (automatically injected by `@require_session`).
    - `permission_name` (`str`): The name of the permission to create.
    - `**kwargs`: Permission settings as key-value pairs (e.g., `can_read=True`, `can_write=False`).

    **Returns:**
    - `JsonResponse`:
      - **Success (201)**: `{'name': str, 'status': 201}`
      - **Error (400)**: `{'status': 400, 'reason': 'Creation of permission "{permission_name}" failed.'}`
      - **Error (401)**: `{'status': 403, 'reason': 'Session is not valid'}`
      - **Error (403)**: `{'status': 403, 'reason': 'User does not have role'}`

    **Example:**
    ```
    POST /api/v1/users/groups/create_permission
    {
        "permission_name": "read_access",
        "can_read": true,
        "can_write": false,
        "can_delete": false
    }
    ```
    """
    logger.info(f"Creating new group permission '{permission_name}'")
    permission = Permissions.from_keys(default_if_key_not_present=False, **kwargs)
    return AuthApi().create_group_permission(State.state, permission_name=permission_name, permissions=permission)


@app.post('/api/v1/users/groups/create_group')
@json_endpoint
@require_session
@require_user_role(Roles.can_create_group)
async def create_group(session_user: User, group_name: str, permissions: str) -> JsonResponse:
    """
    ### Create a new group

    Creates a new group with the specified name and associated permissions.
    Requires an active session and the `can_create_group` role.

    **Args:**
    - `session_user` (`User`): The authenticated user (automatically injected by `@require_session`).
    - `group_name` (`str`): The name of the group to create.
    - `permissions` (`str`): The name of the permission group to associate with this group.

    **Returns:**
    - `JsonResponse`:
      - **Success (201)**: `{'name': str, 'status': 201}`
      - **Error (400)**: `{'status': 400, 'reason': 'Creation of group "{group_name}" failed.'}`
      - **Error (401)**: `{'status': 401, 'reason': 'Session is not valid'}`
      - **Error (403)**: `{'status': 403, 'reason': 'User does not have role'}`
      - **Error (404)**: `{'status': 404, 'reason': 'Permission group does not exist'}`

    **Example:**
    ```
    POST /api/v1/users/groups/create_group
    {
        "group_name": "editors",
        "permissions": "edit_permissions"
    }
    ```
    """
    logger.info(f'Creating new group {group_name} with permissions {permissions}')
    return AuthApi().create_group(state=State.state, group_name=group_name, permission_group=permissions)


@app.post('/api/v1/users/join_group')
@json_endpoint
@require_session
async def join_group(session_user: User, group_name: str) -> WebResponse:
    """
    ### Join a group

    Adds the authenticated user to the specified group. Requires an active session.

    **Args:**
    - `session_user` (`User`): The authenticated user (automatically injected by `@require_session`).
    - `group_name` (`str`): The name of the group to join.

    **Returns:**
    - `WebResponse`:
      - **Success (200)**: Empty response body
      - **Error (403)**: `{'status': 403, 'reason': 'Session is not valid'}`
      - **Error (404)**: `{'status': 404, 'reason': 'Group does not exist'}`
      - **Error (400)**: `{'status': 400, 'reason': 'Group assignment failed'}`

    **Example:**
    ```
    POST /api/v1/users/join_group
    {
        "group_name": "editors"
    }
    ```
    """
    logger.info(f'User {session_user.id} is joining group {group_name}')
    return AuthApi().join_group(state=State.state, user=session_user, group_name=group_name)


@app.post('/api/v1/users/leave_group')
@json_endpoint
@require_session
async def leave_group(session_user: User, group_name: str) -> WebResponse:
    """
    ### Leave a group

    Removes the authenticated user from the specified group. Requires an active session.

    **Args:**
    - `session_user` (`User`): The authenticated user (automatically injected by `@require_session`).
    - `group_name` (`str`): The name of the group to leave.

    **Returns:**
    - `WebResponse`:
      - **Success (200)**: Empty response body
      - **Error (403)**: `{'status': 403, 'reason': 'Session is not valid'}`
      - **Error (404)**: `{'status': 404, 'reason': 'Group does not exist'}`

    **Example:**
    ```
    POST /api/v1/users/leave_group
    {
        "group_name": "editors"
    }
    ```
    """
    logger.info(f'User {session_user.id} is leaving group {group_name}')
    return AuthApi().leave_group(state=State.state, user=session_user, group_name=group_name)


# required to bootstrap server
@app.post('/api/local/users/create_bot')
@url_endpoint
@require_local
async def local_create_bot() -> JsonResponse:
    """
    ### Create a new bot user (Local only)

    Creates a new user and links a bot user to it, returning the bot token.
    This endpoint is only available for local requests (internal server bootstrapping).

    **Returns:**
    - `JsonResponse`:
      - **Success (201)**: `{'bot_token': str, 'status': 201}`
      - **Error (400)**: `{'status': 400, 'reason': 'An internal error occurred'}`
      - **Error (403)**: `{'status': 403, 'reason': 'Access denied - local access only'}`

    **Example:**
    ```
    POST /api/local/users/create_bot
    ```
    """
    logger.info('Creating new bot user (Local)')
    return AuthApi().create_new_user_bot(state=State.state)


@app.post('/api/local/users/create_role')
@json_endpoint
@require_local
@require_session
async def local_create_role(session_user: User, role_name: str, **kwargs) -> JsonResponse:
    """
    ### Create a new role (Local only)

    Creates a new role with the specified name and role permissions.
    This endpoint is only available for local requests (internal server administration).

    **Args:**
    - `session_user` (`User`): The authenticated user (automatically injected by `@require_session`).
    - `role_name` (`str`): The name of the role to create.
    - `**kwargs`: Role permissions as key-value pairs (e.g., `can_create_group=True`).

    **Returns:**
    - `JsonResponse`:
      - **Success (201)**: `{'name': str, 'status': 201}`
      - **Error (400)**: `{'status': 400, 'reason': 'Creation of role "{role_name}" failed.'}`
      - **Error (401)**: `{'status': 401, 'reason': 'Session is not valid'}`
      - **Error (403)**: `{'status': 403, 'reason': 'Access denied: only local'}`

    **Example:**
    ```
    POST /api/local/users/create_role
    {
        "role_name": "admin",
        "can_create_group": true,
        "can_manage_users": true
    }
    ```
    """
    logger.info('Creating new role (Local)')
    role = Roles.from_keys(**kwargs)
    return AuthApi().create_role(State.state, role_name=role_name, roles=role)


@app.post('/api/local/users/assign_role')
@json_endpoint
@require_local
@require_session
async def local_assign_role(session_user: User, role_name: str, user_uuid: str) -> WebResponse:
    """
    ### Assign a role to a user (Local only)

    Assigns the specified role to the user with the given UUID.
    This endpoint is only available for local requests (internal server administration).

    **Args:**
    - `session_user` (`User`): The authenticated user (automatically injected by `@require_session`).
    - `role_name` (`str`): The name of the role to assign.
    - `user_uuid` (`str`): The UUID of the user to assign the role to.

    **Returns:**
    - `WebResponse`:
      - **Success (200)**: Empty response body
      - **Error (401)**: `{'status': 401, 'reason': 'Session is not valid'}`
      - **Error (403)**: `{'status': 403, 'reason': 'Access denied - local access only'}`
      - **Error (404)**: `{'status': 404, 'reason': 'User does not exist'}` or `{'status': 404, 'reason': 'Role does not exist'}`

    **Example:**
    ```
    POST /api/local/users/assign_role
    {
        "role_name": "admin",
        "user_uuid": "12345678-1234-5678-9012-123456789012"
    }
    ```
    """
    logger.info(f'Assigning {role_name} to user {user_uuid} (Local)')
    return AuthApi().assign_role(State.state, role_name=role_name, user_uuid=uuid.UUID(hex=user_uuid))
