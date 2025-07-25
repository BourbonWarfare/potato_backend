import logging
from bw.error import NonLocalIpAccessingLocalOnlyAddress, CannotDetermineSession, NotEnoughPermissions
from bw.state import State
from bw.models.auth import User
from bw.auth.validators import validate_local, validate_session
from bw.auth.session import SessionStore
from bw.auth.group import GroupStore
from bw.auth.user import UserStore
from quart import request

logger = logging.getLogger('bw.auth')


def require_local(func):
    """
    ### Restrict access to local network requests

    Restricts access to the decorated function to requests originating from the local network only.

    **Raises:**
    - `NonLocalIpAccessingLocalOnlyAddress`: If the request is not from a local IP address.

    **Example:**
    ```python
    @require_local
    def my_view(...):
        ...
    ```
    """

    async def wrapper(*args, **kwargs):
        try:
            validate_local(request.remote_addr)
        except NonLocalIpAccessingLocalOnlyAddress as e:
            logger.warning(f'Non-local API called from abroad: {e}')
            raise e
        return await func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper


def require_session(func):
    """
    ### Require a valid session token

    Ensures the decorated function is called with a valid session token.

    **Raises:**
    - `CannotDetermineSession`: If the request is malformed such that we can't determine session.
    - `SessionKnownButInvalid`: If the session is not valid for some reason.

    **Example:**
    ```python
    @require_session
    def my_view(session_user, ...):
        ...
    ```
    """

    async def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization')
        if auth is None:
            logger.warning("'Session Token' not present in header")
            raise CannotDetermineSession()

        bearer_header = 'Bearer '
        if not auth.startswith(bearer_header):
            logger.warning("'Session Token' does not start with 'Bearer '")
            raise CannotDetermineSession()

        session_token = auth[len(bearer_header) :]  # Remove 'Bearer ' prefix

        validate_session(State.state, session_token)
        session_user = SessionStore().get_user_from_session_token(State.state, session_token=session_token)
        return await func(session_user=session_user, *args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper


def require_group_permission(*required_permissions: bool):
    """
    ### Require group permissions

    Decorator factory that enforces group-based permissions for the decorated function.

    **Raises:**
    - `NotEnoughPermissions`: If any required permission is missing from the user's group permissions.

    **Example:**
    ```python
    @require_group_permission(Permissions.can_upload_mission, Permissions.can_test_mission)
    def my_view(session_token, ...):
        ...
    ```
    """

    def decorator(func):
        async def wrapper(session_user: User, *args, **kwargs):
            permissions = GroupStore().get_all_permissions_user_has(State.state, session_user)
            for permission in required_permissions:
                if not permission.__get__(permissions):  # ty: ignore[unresolved-attribute]
                    logger.warning(f'User {session_user.id} does not have required permission: {permission.__name__}')  # ty: ignore[unresolved-attribute]
                    raise NotEnoughPermissions()
            return await func(session_user=session_user, *args, **kwargs)

        wrapper.__name__ = func.__name__
        return wrapper

    return decorator


def require_user_role(*required_roles: bool):
    """
    ### Require group permissions

    Decorator factory that enforces group-based permissions for the decorated function.

    **Raises:**
    - `NotEnoughPermissions`: If any required permission is missing from the user's group permissions.

    **Example:**
    ```python
    @require_group_permission(Permissions.can_upload_mission, Permissions.can_test_mission)
    def my_view(session_token, ...):
        ...
    ```
    """

    def decorator(func):
        async def wrapper(session_user: User, *args, **kwargs):
            user_role = UserStore().get_users_role(State.state, session_user)
            if user_role is None:
                logger.warning(f'User {session_user.id} does not have a role assigned')
                raise NotEnoughPermissions()
            roles = user_role.into_roles()
            for role in required_roles:
                if not role.__get__(roles):  # ty: ignore[unresolved-attribute]
                    logger.warning(f'User {session_user.id} does not have required role: {role.__name__}')  # ty: ignore[unresolved-attribute]
                    raise NotEnoughPermissions()
            return await func(session_user=session_user, *args, **kwargs)

        wrapper.__name__ = func.__name__
        return wrapper

    return decorator
