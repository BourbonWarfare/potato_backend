from uuid import UUID
from bw.error.base import ClientError


class SessionError(ClientError):
    def __init__(self, message: str):
        super().__init__(f'An error occured while managing ARMA session: {message}')


class SessionDoesNotExist(SessionError):
    def __init__(self, uuid: UUID):
        super().__init__(f'session does not exist {uuid}')


class NoSessionsRegistered(SessionError):
    def __init__(self):
        super().__init__('no session has been registered')


class SessionAlreadyEnded(SessionError):
    def __init__(self):
        super().__init__('session has already ended')
