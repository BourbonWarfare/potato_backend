class BwServerError(Exception):
    pass

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

class AuthError(BwServerError):
    def __init__(self, reason: str):
        super().__init__(f'Authentication error: {reason}')

class NonLocalIpAccessingLocalOnlyAddress(AuthError):
    def __init__(self):
        super().__init__('Attempting to access local-only endpoint from abroad')
