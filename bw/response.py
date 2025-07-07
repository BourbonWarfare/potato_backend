from quart import Response
from werkzeug.datastructures.headers import Headers
import json


class WebResponse(Response):
    def content_type(self) -> str:
        return 'text/plain'

    def __init__(self, status: int, headers: dict = {}, response='', **kwargs):
        lower_headers = {key.lower(): value for key, value in headers.items()}
        if 'content-type' not in lower_headers:
            lower_headers['content-type'] = self.content_type()

        super().__init__(
            response=response,
            status=status,
            headers=Headers([(k, v) for k, v in lower_headers.items()]),
            mimetype=self.content_type(),
            **kwargs,
        )


class Ok(WebResponse):
    def __init__(self, data: str = ''):
        super().__init__(200, response=data)


class Created(WebResponse):
    def __init__(self, data: str = ''):
        super().__init__(201, response=data)


class JsonResponse(WebResponse):
    def content_type(self) -> str:
        return 'text/json'

    def __init__(self, json_payload: dict, headers: dict = {}, status=200):
        if 'status' not in json_payload:
            json_payload['status'] = status
        self.contained_json = json_payload
        super().__init__(status=200, headers=headers, response=json.dumps(json_payload))


class HtmlResponse(WebResponse):
    def content_type(self) -> str:
        return 'text/html'

    def __init__(self, html: str, headers: dict = {}):
        super().__init__(status=200, headers=headers, response=html)
