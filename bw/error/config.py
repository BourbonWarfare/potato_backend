from bw.error.base import BwServerError


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


class WrongConfigType(ConfigError):
    def __init__(self, expected_type: str, actual_type: str):
        super().__init__(f'Expected config type {expected_type}, but got {actual_type}')


class ConfigIsNotEnv(WrongConfigType):
    def __init__(self, actual: str):
        super().__init__('.env', actual)


class ConfigIsNotKeyValue(WrongConfigType):
    def __init__(self, actual: str):
        super().__init__('.txt', actual)


class ConfigIsNotToml(WrongConfigType):
    def __init__(self, actual: str):
        super().__init__('.toml', actual)


class UnknownConfigFileType(WrongConfigType):
    def __init__(self, actual: str, *expected: str):
        ConfigError.__init__(self, f'Unknown config file type: {actual}. Expected one of: {", ".join(expected)}')
