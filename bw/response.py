from web.webapi import ctx, header
import json

class WebResponse:
    def content_type(self) -> str:
        return 'text/plain'

    def __init__(self, status: int, headers: dict, data=""):
        ctx.status = status

        lower_headers = { key.lower(): value for key, value in headers.items() }
        if 'content-type' not in lower_headers:
            lower_headers['content-type'] = self.content_type()

        for key, value in lower_headers.items():
            header(key, value)
        self.data = data

    def into(self) -> str:
        return self.data

class Ok(WebResponse):
    def __init__(self):
        super().__init__(200, {})

class JsonResponse(WebResponse):
    def content_type(self) -> str:
        return 'text/json'

    def __init__(self, json_payload: dict, headers: dict = {}, status=200):
        if 'status' not in json_payload:
            json_payload['status'] = status
        super().__init__(status=200, headers=headers, data=json.dumps(json_payload))

class HtmlResponse(WebResponse):
    def content_type(self) -> str:
        return 'text/html'

    def __init__(self, html: str, headers: dict = {}):
        super().__init__(status=200, headers=headers, data=html)
