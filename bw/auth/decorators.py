import logging
import asyncio
import functools
from contextlib import contextmanager
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

    @contextmanager
    def _validate_local():
        print(request.remote_addr)
        try:
            validate_local(request.remote_addr)
        except NonLocalIpAccessingLocalOnlyAddress as e:
            logger.warning(f'Non-local API called from abroad: {e}')
            raise e
        yield

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with _validate_local():
            if asyncio.iscoroutinefunction(func):

                async def afnc():
                    return await func(*args, **kwargs)

                return afnc()
            else:
                return func(*args, **kwargs)

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

    @contextmanager
    def _session_user():
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
        yield SessionStore().get_user_from_session_token(State.state, session_token=session_token)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with _session_user() as session_user:
            if asyncio.iscoroutinefunction(func):

                async def afnc():
                    return await func(session_user=session_user, *args, **kwargs)

                return afnc()
            else:
                return func(session_user=session_user, *args, **kwargs)

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

    @contextmanager
    def _validate_permissions(session_user: User):
        permissions = GroupStore().get_all_permissions_user_has(State.state, session_user)
        for permission in required_permissions:
            if not permission.__get__(permissions):  # ty: ignore[unresolved-attribute]
                logger.warning(f'User {session_user.id} does not have required permission: {permission.__name__}')  # ty: ignore[unresolved-attribute]
                raise NotEnoughPermissions()
        yield

    def decorator(func):
        @functools.wraps(func)
        def wrapper(session_user: User, *args, **kwargs):
            with _validate_permissions(session_user):
                if asyncio.iscoroutinefunction(func):

                    async def afnc():
                        return await func(session_user=session_user, *args, **kwargs)

                    return afnc()
                else:
                    return func(session_user=session_user, *args, **kwargs)

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

    @contextmanager
    def _validate_roles(session_user: User):
        user_role = UserStore().get_users_role(State.state, session_user)
        if user_role is None:
            logger.warning(f'User {session_user.id} does not have a role assigned')
            raise NotEnoughPermissions()
        for role in required_roles:
            if not role.__get__(user_role):  # ty: ignore[unresolved-attribute]
                logger.warning(f'User {session_user.id} does not have required role: {role.__name__}')  # ty: ignore[unresolved-attribute]
                raise NotEnoughPermissions()
        yield

    def decorator(func):
        @functools.wraps(func)
        def wrapper(session_user: User, *args, **kwargs):
            with _validate_roles(session_user):
                if asyncio.iscoroutinefunction(func):

                    async def afnc():
                        return await func(session_user=session_user, *args, **kwargs)

                    return afnc()
                else:
                    return func(session_user=session_user, *args, **kwargs)

        return wrapper

    return decorator
