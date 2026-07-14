from bw.error.base import ClientError


class HemttError(ClientError):
    def __init__(self, reason: str):
        super().__init__(f'{reason}')
