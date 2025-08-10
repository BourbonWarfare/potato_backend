from bw.error.base import BwServerError


class ServerManageError(BwServerError):
    def __init__(self, reason: str):
        super().__init__(f'Server Manage error: {reason}')


class ServerStartError(ServerManageError):
    def __init__(self, error_message: str):
        super().__init__(f'Failed to start server: {error_message}')


class ServerStopError(ServerManageError):
    def __init__(self, error_message: str):
        super().__init__(f'Failed to stop server: {error_message}')


class ServerRestartError(ServerManageError):
    def __init__(self, error_message: str):
        super().__init__(f'Failed to restart server: {error_message}')
