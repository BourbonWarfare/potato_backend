import web
import json

from bw.error import ExpectedJson, JsonPayloadError

def web_response(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs).into()
    return wrapper

def convert_json_to_args(func):
    def wrapper(*args, **kwargs):
        is_json = 'text/json' == web.ctx.get('content-type', 'text/plain')
        if is_json:
            data = web.data()
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                return ExpectedJson().as_response_code()

            for key in payload.keys():
                if key in kwargs:
                    return JsonPayloadError().as_response_code()

            kwargs.update(payload)
            return func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    return wrapper