from bw.error.base import BwServerError


class RemoteConnectionError(BwServerError):
    def __init__(self, reason: str):
        super().__init__(f'An error occurred while processing a remote connection event: {reason}')


class RemoteConnectionEventParseError(RemoteConnectionError):
    def __init__(self, reason: str):
        super().__init__(f'Failed to parse event: {reason}')


class RemoteConnectionEventMissingField(RemoteConnectionEventParseError):
    def __init__(self, field: str):
        super().__init__(f'Required field "{field}" is missing.')


class RemoteConnectionEventInvalidField(RemoteConnectionEventParseError):
    def __init__(self, field: str, value: str):
        super().__init__(f'Field "{field}" has an invalid value: "{value}".')
