import asyncio
import functools
import logging
from contextlib import contextmanager

from quart import request

from bw.auth.api import AuthApi
from bw.auth.group import GroupStore
from bw.auth.session import SessionStore
from bw.auth.user import UserStore
from bw.auth.utils import session_token_from_bearer, session_token_from_cookie
from bw.auth.validators import validate_local, validate_session
from bw.error import (
    CannotDetermineSession,
    CsrfTokenDoesntMatch,
    NeedsAuthenticatedSession,
    NonLocalIpAccessingLocalOnlyAddress,
    NotEnoughPermissions,
    SessionExpired,
)
from bw.models.auth import User
from bw.state import State

logger = logging.getLogger('bw.auth')


def with_token(func):
    """
    ### Add the session token to the function arguments

    **Raises:**
    - `CannotDetermineSession`: If the request is malformed such that we can't determine session.

    **Example:**
    ```python
    @with_token
    def my_view(token, ...):
        ...
    ```
    """

    @functools.wraps(func)
    def wrapper(**kwargs):
        auth = request.headers.get('Authorization')
        if auth is None:
            logger.warning("'Session Token' not present in header")
            raise CannotDetermineSession()

        bearer_header = 'Bearer '
        if not auth.startswith(bearer_header):
            logger.warning("'Session Token' does not start with 'Bearer '")
            raise CannotDetermineSession()

        session_token = auth[len(bearer_header) :]  # Remove 'Bearer ' prefix
        if asyncio.iscoroutinefunction(func):

            async def afnc():
                return await func(token=session_token, **kwargs)

            return afnc()
        else:
            return func(token=session_token, **kwargs)

    return wrapper


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
        try:
            validate_local(request.remote_addr)
        except NonLocalIpAccessingLocalOnlyAddress as err:
            logger.warning(f'Non-local API called from abroad: {err}')
            raise
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
        try:
            session_token = session_token_from_cookie(AuthApi())
        except CannotDetermineSession:
            session_token = session_token_from_bearer(request.headers)

        validate_session(State.state, session_token)
        yield SessionStore().get_user_from_session_token(State.state, session_token=session_token)

    @functools.wraps(func)
    def wrapper(**kwargs):
        with _session_user() as session_user:
            if asyncio.iscoroutinefunction(func):

                async def afnc():
                    return await func(session_user=session_user, **kwargs)

                return afnc()
            else:
                return func(session_user=session_user, **kwargs)

    return wrapper


def with_default_session(func):
    """
    ### Start an unauthenticated session with this request

    Ensures a session is created for this user by starting an unauthenticated one if none are found
    in the cookie

    **Example:**
    ```python
    @with_default_session
    def my_view(session_token: str, ...):
        ...
    ```
    """

    @contextmanager
    def _session_token():
        session_token: str | None = None
        try:
            session_token = session_token_from_cookie(AuthApi())
        except CannotDetermineSession:
            pass

        if not session_token:
            try:
                session_token = session_token_from_bearer(headers=request.headers)
            except CannotDetermineSession:
                pass

        try:
            if not session_token:
                raise NeedsAuthenticatedSession()

            validate_session(State.state, session_token, require_authentication=False)
        except (SessionExpired, NeedsAuthenticatedSession):
            session = SessionStore().start_unauthenticated_session(State.state)
            session_token = session['session_token']

        yield session_token

    @functools.wraps(func)
    def wrapper(**kwargs):
        with _session_token() as session_token:
            if asyncio.iscoroutinefunction(func):

                async def afnc():
                    return await func(session_token=session_token, **kwargs)

                return afnc()
            else:
                return func(session_token=session_token, **kwargs)

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
        def wrapper(session_user: User, **kwargs):
            with _validate_permissions(session_user):
                if asyncio.iscoroutinefunction(func):

                    async def afnc():
                        return await func(session_user=session_user, **kwargs)

                    return afnc()
                else:
                    return func(session_user=session_user, **kwargs)

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
        def wrapper(session_user: User, **kwargs):
            with _validate_roles(session_user):
                if asyncio.iscoroutinefunction(func):

                    async def afnc():
                        return await func(session_user=session_user, **kwargs)

                    return afnc()
                else:
                    return func(session_user=session_user, **kwargs)

        return wrapper

    return decorator


def verify_csrf_from_form(form_id: str = 'csrf_token'):
    def decorator(func):
        @contextmanager
        def _session_csrf():
            session_token: str = ''
            try:
                session_token = session_token_from_cookie(AuthApi())
            except CannotDetermineSession:
                pass

            if not session_token:
                try:
                    session_token = session_token_from_bearer(headers=request.headers)
                except CannotDetermineSession:
                    pass

            try:
                if not session_token:
                    raise NeedsAuthenticatedSession()

                validate_session(State.state, session_token)
            except (SessionExpired, NeedsAuthenticatedSession):
                pass

            yield SessionStore().get_csrf_token(State.state, session_token)

        @functools.wraps(func)
        async def wrapper(**kwargs):
            with _session_csrf() as csrf_token:
                print(request.form)
                form_token = (await request.form).get(form_id, '')
                print(csrf_token, form_token)
                if form_token != csrf_token:
                    raise CsrfTokenDoesntMatch()

            if asyncio.iscoroutinefunction(func):
                return await func(**kwargs)
            else:
                return func(**kwargs)

        return wrapper

    return decorator
