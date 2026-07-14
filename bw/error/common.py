from bw.error.base import ClientError


class DbError(ClientError):
    def __init__(self):
        super().__init__('An internal error occured')
