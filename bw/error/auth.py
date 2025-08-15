from bw.error.base import ClientError, ConflictError, NotFoundError
from typing import Any


class AuthError(ClientError):
    def __init__(self, reason: str):
        super().__init__(f'Error with authorization: {reason}')


class DiscordUserAlreadyExists(ConflictError):
    def __init__(self, discord_id: int, user_id: int):
        super().__init__(f'Discord user with id {discord_id} already exists for user {user_id}')


class GroupCreationFailed(ConflictError):
    def __init__(self, group_name: str):
        super().__init__(f'Creation of group "{group_name}" failed.')


class GroupAssignmentFailed(ConflictError):
    def __init__(self):
        super().__init__('Failed to assign user to group.')


class GroupPermissionCreationFailed(ConflictError):
    def __init__(self, permission_name: str):
        super().__init__(f'Creation of permission "{permission_name}" failed.')


class RoleCreationFailed(ConflictError):
    def __init__(self, role_name: str):
        super().__init__(f'Creation of role "{role_name}" failed.')


class ForbiddenError(AuthError):
    def status(self) -> int:
        return 403

    def __init__(self, reason: str):
        super().__init__(f'Forbidden: {reason}')


class NotEnoughPermissions(ForbiddenError):
    def __init__(self):
        super().__init__('User does not have enough permissions to access this resource')


class NonLocalIpAccessingLocalOnlyAddress(ForbiddenError):
    def __init__(self, ip: str):
        super().__init__(f'Attempting to access local-only endpoint from abroad ({ip})')


class ReauthNeededError(AuthError):
    def status(self) -> int:
        return 401

    def headers(self) -> dict[str, str]:
        return {'WWW-Authenticate': f'Bearer realm="", authorization_uri="{self.reauth_uri}"'}

    def __init__(self, reason: str, reauth_uri: str = '/api/v1/users/auth/'):
        self.reauth_uri = reauth_uri
        super().__init__(reason)


class NotEnoughDetails(ReauthNeededError):
    def __init__(self):
        super().__init__('Not enough details provided to authenticate user')


class CannotDetermineSession(ReauthNeededError):
    def __init__(self):
        super().__init__('Cannot determine user session from request. Please provide a valid session token.')


class SessionExpired(ReauthNeededError):
    def __init__(self):
        super().__init__('Session token has expired.')


class NoGroupPermissionWithCredentials(NotFoundError):
    def __init__(self, group_name: str):
        super().__init__(f'No group permission called "{group_name}" exists.')


class NoGroupWithName(NotFoundError):
    def __init__(self, group_name: str):
        super().__init__(f'No group called "{group_name}" exists.')


class NoUserWithGivenCredentials(NotFoundError):
    def __init__(self, user_id: Any | None):
        if user_id is not None:
            super().__init__(f'User [id: "{user_id}"] does not exist')
        else:
            super().__init__('User does not exist')


class NoRoleWithName(NotFoundError):
    def __init__(self, role_name: str):
        super().__init__(f'No role with name "{role_name}" exists.')
