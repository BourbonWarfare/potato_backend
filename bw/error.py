from bw.response import WebResponse, JsonResponse


class BwServerError(Exception):
    def status(self) -> int:
        return 500

    def as_json(self) -> JsonResponse:
        return JsonResponse({'status': self.status(), 'reason': str(self)})

    def as_response_code(self) -> WebResponse:
        return WebResponse(status=self.status())


class ExpectedJson(BwServerError):
    def __init__(self):
        super().__init__(f'Expected JSON payload, got something else')


class JsonPayloadError(BwServerError):
    def __init__(self):
        super().__init__(f'JSON payload malformed')


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
        super().__init__(f'Config not loaded')


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
        super().__init__(f'[Auth] Error: {reason}')


class SessionInvalid(AuthError):
    def __init__(self):
        super().__init__('Session is not valid')


class InvalidPermissions(AuthError):
    def status(self) -> int:
        return 403

    def __init__(self):
        super().__init__('User has invalid permissions')


class NoUserWithGivenCredentials(AuthError):
    def status(self) -> int:
        return 404

    def __init__(self):
        super().__init__('User does not exist')


class NonLocalIpAccessingLocalOnlyAddress(AuthError):
    def __init__(self):
        super().__init__('Attempting to access local-only endpoint from abroad')
