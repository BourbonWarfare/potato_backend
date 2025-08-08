from bw.response import WebResponse


class BwServerError(Exception):
    def status(self) -> int:
        return self._status

    def headers(self) -> dict[str, str]:
        return {}

    def as_response_code(self) -> WebResponse:
        return WebResponse(status=self.status(), from_exception=self)

    def __init__(self, message: str, status: int = 500):
        super().__init__(message)
        self._status = status


class ClientError(BwServerError):
    def status(self) -> int:
        return 400


class ConflictError(ClientError):
    def status(self) -> int:
        return 409

    def __init__(self, reason: str):
        super().__init__(f'Conflict: {reason}')


class NotFoundError(ClientError):
    def status(self) -> int:
        return 404

    def __init__(self, reason: str):
        super().__init__(f'Not found: {reason}')
