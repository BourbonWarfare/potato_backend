from bw.error.base import ClientError


class AuthError(ClientError):
    def status(self) -> int:
        return 401

    def __init__(self, reason: str):
        super().__init__(f'Error with authorization: {reason}')


class DiscordUserAlreadyExists(AuthError):
    def status(self) -> int:
        return 409

    def __init__(self, discord_id: int, user_id: int):
        super().__init__(f'Discord user with id {discord_id} already exists for user {user_id}')


class NotEnoughPermissions(PermissionError):
    def __init__(self):
        super().__init__('User does not have enough permissions to access this resource')


class NotEnoughDetails(AuthError):
    def __init__(self):
        super().__init__('Not enough details provided to authenticate user')


class SessionInvalid(AuthError):
    def status(self) -> int:
        return 403

    def __init__(self):
        super().__init__('Session is not valid')


class NoUserWithGivenCredentials(AuthError):
    def status(self) -> int:
        return 404

    def __init__(self):
        super().__init__('User does not exist')


class NonLocalIpAccessingLocalOnlyAddress(AuthError):
    def __init__(self, ip: str):
        super().__init__(f'Attempting to access local-only endpoint from abroad ({ip})')


class NoGroupPermissionWithCredentials(AuthError):
    def __init__(self, group_name: str):
        super().__init__(f'No group permission called "{group_name}" exists.')


class NoGroupWithName(AuthError):
    def __init__(self, group_name: str):
        super().__init__(f'No group called "{group_name}" exists.')


class GroupCreationFailed(AuthError):
    def __init__(self, group_name: str):
        super().__init__(f'Creation of group "{group_name}" failed.')


class GroupAssignmentFailed(AuthError):
    def __init__(self):
        super().__init__('Failed to assign user to group.')


class GroupPermissionCreationFailed(AuthError):
    def __init__(self, permission_name: str):
        super().__init__(f'Creation of permission "{permission_name}" failed.')


class RoleCreationFailed(AuthError):
    def __init__(self, role_name: str):
        super().__init__(f'Creation of role "{role_name}" failed.')


class NoRoleWithName(AuthError):
    def status(self) -> int:
        return 404

    def __init__(self, role_name: str):
        super().__init__(f'No role with name "{role_name}" exists.')
