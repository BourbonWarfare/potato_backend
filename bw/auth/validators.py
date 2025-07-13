from bw.error import NonLocalIpAccessingLocalOnlyAddress, SessionExpired, NotEnoughPermissions
from bw.state import State
from bw.auth import api
from bw.auth.roles import Roles
from bw.auth.permissions import Permissions


def validate_user_has_permissions(state: State, session_token: str, permissions: Permissions):
    """
    ### Validate user permissions

    Validates that the user associated with the given session token has all specified permissions.
    Raises `NotEnoughPermissions` if the user does not have the required permissions.

    **Args:**
    - `state` (`State`): The application state containing the database connection.
    - `session_token` (`str`): The session token of the user.
    - `permissions` (`Permissions`): The permissions to check for.

    **Raises:**
    - `NotEnoughPermissions`: If the user does not have the required permissions.
    """
    if not api.AuthApi().does_user_have_permissions(state, session_token, permissions):
        raise NotEnoughPermissions()


def validate_user_has_role(state: State, session_token: str, roles: Roles):
    """
    ### Validate user roles

    Validates that the user associated with the given session token has all specified roles.
    Raises `NotEnoughPermissions` if the user does not have the required roles.

    **Args:**
    - `state` (`State`): The application state containing the database connection.
    - `session_token` (`str`): The session token of the user.
    - `roles` (`Roles`): The roles to check for.

    **Raises:**
    - `NotEnoughPermissions`: If the user does not have the required roles.
    """
    if not api.AuthApi().does_user_have_roles(state, session_token, roles):
        raise NotEnoughPermissions()


def validate_session(state: State, session_token: str):
    """
    ### Validate session token

    Validates that the session token is active and not expired or revoked.
    Raises `SessionInvalid` if the session is not valid.

    **Args:**
    - `state` (`State`): The application state containing the database connection.
    - `session_token` (`str`): The session token to validate.

    **Raises:**
    - `SessionInvalid`: If the session is not valid.
    """
    if not api.AuthApi().is_session_active(state, session_token):
        raise SessionExpired()


def validate_local(ip: str | None):
    """
    ### Validate local IP address

    Validates that the request context is from a local IP address.
    Raises `NonLocalIpAccessingLocalOnlyAddress` if the request is not from a local IP.

    **Args:**
    - `ip` (`str | None`): The IP address to validate.

    **Raises:**
    - `NonLocalIpAccessingLocalOnlyAddress`: If the request is not from a local IP address.
    """
    if ip is None:
        raise NonLocalIpAccessingLocalOnlyAddress('IP address not present')

    valid_local_prefix = (
        '0.',
        '10.',
        '127.',
        '172.16.',
        '192.0.0.',
        '192.168.',
    )
    if not any([ip.startswith(prefix) for prefix in valid_local_prefix]):
        raise NonLocalIpAccessingLocalOnlyAddress(ip)
