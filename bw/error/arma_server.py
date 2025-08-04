from bw.error import BwServerError


class ArmaServerError(BwServerError):
    def __init__(self, reason: str):
        super().__init__(f'An error occured with the ArMa server: {reason}')


class ArmaServerUnresponsive(ArmaServerError):
    def __init__(self):
        super().__init__('The Arma server is unresponsive.')
