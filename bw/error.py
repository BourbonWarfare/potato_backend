from bw.response import WebResponse, JsonResponse


class BwServerError(Exception):
    def status(self) -> int:
        return 500

    def as_json(self) -> JsonResponse:
        return JsonResponse({'status': self.status(), 'reason': str(self)})

    def as_response_code(self) -> WebResponse:
        return WebResponse(status=self.status())


class BadArguments(BwServerError):
    def status(self) -> int:
        return 400

    def __init__(self):
        super().__init__('Arguments are invalid')


class MismatchedArguments(BwServerError):
    def status(self) -> int:
        return 400

    def __init__(self, expected_keys=[], extra_keys=[]):
        if expected_keys == [] and extra_keys == []:
            raise BadArguments()
        elif expected_keys == [] and extra_keys != []:
            super().__init__(f'Extra keys supplied: {"', '".join(extra_keys)}')
        elif expected_keys != [] and extra_keys == []:
            super().__init__(f'Keys expected but not supplied: {", ".join(expected_keys)}')
        else:
            super().__init__(
                f'Keys expected but not supplied: {", ".join(expected_keys)}. Extra keys supplied: {", ".join(extra_keys)}'
            )


class ExpectedJson(BwServerError):
    def status(self) -> int:
        return 415

    def __init__(self):
        super().__init__('Expected JSON payload, got something else')


class JsonPayloadError(BwServerError):
    def status(self) -> int:
        return 400

    def __init__(self):
        super().__init__('JSON payload malformed')


class ConfigError(BwServerError):
    def __init__(self, reason: str):
        super().__init__(f'Configuration error: {reason}')


class DuplicateConfigKey(ConfigError):
    def __init__(self, key):
        super().__init__(f'Duplicate key: {key}')


class ConfigurationKeyNotPresent(ConfigError):
    def __init__(self, key):
        super().__init__(f'Key not present: {key}')


class NoConfigLoaded(ConfigError):
    def __init__(self):
        super().__init__('Config not loaded')


class ClientError(BwServerError):
    def status(self) -> int:
        return 400


class DbError(ClientError):
    def status(self) -> int:
        return 400

    def __init__(self):
        super().__init__('An internal error occured')


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


class MissionError(ClientError):
    def __init__(self, reason: str):
        super().__init__(f'An issue with the mission api occured: {reason}')


class CouldNotCreateMissionType(MissionError):
    def __init__(self):
        super().__init__('couldnt create mission type')


class NoMissionTypeWithName(MissionError):
    def status(self) -> int:
        return 404

    def __init__(self, name: str):
        super().__init__('no mission type called "{name}" exists')


class NoMissionTypeWithTag(MissionError):
    def status(self) -> int:
        return 404

    def __init__(self, tag: int):
        super().__init__('no mission type with tag "{tag}" exists')


class CouldNotCreateTestResult(MissionError):
    def __init__(self):
        super().__init__('couldnt create test result')


class CouldNotCosignResult(MissionError):
    def __init__(self):
        super().__init__('couldnt cosign test result')


class NoReviewFound(MissionError):
    def status(self) -> int:
        return 404

    def __init__(self):
        super().__init__('couldnt find review')


class CouldNotCreateIteration(MissionError):
    def __init__(self):
        super().__init__('could not create mission iteration')


class MissionDoesNotExist(MissionError):
    def status(self) -> int:
        return 404

    def __init__(self):
        super().__init__('mission does not exist')


class SubprocessError(BwServerError):
    def __init__(self, reason: str):
        super().__init__(f'An error occured calling a subprocess: {reason}')


class SubprocessNotFound(SubprocessError):
    def status(self) -> int:
        return 404

    def __init__(self, subprocess: str):
        super().__init__("could not find an executible version of '{subprocess}'")


class SubprocessFailed(SubprocessError):
    def __init__(self, subprocess: str, reason: str):
        super().__init__(f"process '{subprocess}' didn't exist successfully\n\t{reason}")


class MissionFileError(BwServerError):
    def __init__(self, reason: str):
        super().__init__(f'Some IO went wrong with the mission file: {reason}')


class MissionFileDoesNotExist(MissionFileError):
    def status(self) -> int:
        return 404

    def __init__(self, directory: str):
        super().__init__("mission does not exist at directory '{directory}'")


class UploadError(ClientError):
    def status(self) -> int:
        return 422

    def __init__(self, reason: str):
        super().__init__('Something went wrong with the upload: {reason}')


class MissionDoesNotHaveMetadata(UploadError):
    def __init__(self):
        super().__init__('mission does not have attached mission testing attributes')


class CacheMiss(BwServerError):
    def status(self) -> int:
        return 404


class L1CacheMiss(CacheMiss):
    def __init__(self, key: str):
        super().__init__(f'L1 Cache miss for key: {key}')
