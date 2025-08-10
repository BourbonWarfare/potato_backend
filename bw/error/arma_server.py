from bw.error.base import BwServerError, NotFoundError


class ArmaServerError(BwServerError):
    def __init__(self, reason: str):
        super().__init__(f'An error occured with the ArMa server: {reason}')


class ArmaServerUnresponsive(ArmaServerError):
    def __init__(self):
        super().__init__('The Arma server is unresponsive.')


class ModlistNotFound(NotFoundError):
    def __init__(self, modlist_name: str):
        super().__init__(f'Modlist "{modlist_name}" not found in the server configuration.')


class ServerConfigNotFound(NotFoundError):
    def __init__(self, server_name: str):
        super().__init__(f'Server "{server_name}" not found in the configuration.')
