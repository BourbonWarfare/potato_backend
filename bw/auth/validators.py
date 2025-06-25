from bw.error import NonLocalIpAccessingLocalOnlyAddress, SessionInvalid
from bw.state import State
from bw.auth import api

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
