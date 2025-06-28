from quart import request

from bw.error import ExpectedJson, JsonPayloadError, BwServerError


def url_api(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BwServerError as e:
            return e.as_response_code()

    return wrapper


def json_api(func):
    async def wrapper(*args, **kwargs):
        converted_json = await request.get_json()
        if converted_json is not None:
            for key in converted_json.keys():
                if key in kwargs:
                    return JsonPayloadError().as_json()

            kwargs.update(converted_json)
            try:
                return await func(*args, **kwargs)
            except TypeError:
                return JsonPayloadError().as_json()
            except BwServerError as e:
                return e.as_json()
        else:
            return ExpectedJson().as_json()

    return wrapper
