from bw.error import NonLocalIpAccessingLocalOnlyAddress, SessionInvalid, NotEnoughPermissions
from bw.state import State
from bw.auth import api
from bw.auth.roles import Roles
from bw.auth.permissions import Permissions


def validate_user_has_permissions(state: State, session_token: str, permissions: Permissions):
    if not api.AuthApi().does_user_have_permissions(state, session_token, permissions):
        raise NotEnoughPermissions()


def validate_user_has_role(state: State, session_token: str, roles: Roles):
    if not api.AuthApi().does_user_have_roles(state, session_token, roles):
        raise NotEnoughPermissions()


def validate_session(state: State, session_token: str):
    if not api.AuthApi().is_session_active(state, session_token):
        raise SessionInvalid()


def validate_local(ctx: dict):
    valid_local_prefix = (
        '0.',
        '10.',
        '127.',
        '172.16.',
        '192.0.0.',
        '192.168.',
    )
    ip = ctx.get('ip', '255.255.255.255')
    if not any([ip.startswith(prefix) for prefix in valid_local_prefix]):
        raise NonLocalIpAccessingLocalOnlyAddress(ip)
