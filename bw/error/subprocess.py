from bw.error.base import BwServerError


class SubprocessError(BwServerError):
    def __init__(self, reason: str):
        super().__init__(f'An error occured calling a subprocess: {reason}')


class SubprocessNotFound(SubprocessError):
    def __init__(self, subprocess: str):
        super().__init__("could not find an executible version of '{subprocess}'")


class SubprocessFailed(SubprocessError):
    def __init__(self, subprocess: str, reason: str):
        super().__init__(f"process '{subprocess}' didn't exist successfully\n\t{reason}")
