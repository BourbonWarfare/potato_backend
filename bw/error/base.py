from bw.response import WebResponse, JsonResponse


class BwServerError(Exception):
    def status(self) -> int:
        return 500

    def headers(self) -> dict[str, str]:
        return {}

    def as_json(self) -> JsonResponse:
        return JsonResponse({'status': self.status(), 'reason': str(self)})

    def as_response_code(self) -> WebResponse:
        return WebResponse(status=self.status())


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
