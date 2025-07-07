import logging
from quart import request

from bw.error import ExpectedJson, BadArguments, JsonPayloadError, BwServerError


logger = logging.getLogger('quart.app')


def url_api(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except BwServerError as e:
            logger.warning(f'Error in URL API: {e}')
            return e.as_response_code()

    wrapper.__name__ = func.__name__
    return wrapper


def json_api(func):
    async def wrapper(*args, **kwargs):
        converted_json = await request.get_json()
        if converted_json is not None:
            for key in converted_json.keys():
                if key in kwargs:
                    logger.warning(f'Duplicate key found while parsing arguments: {key}')
                    return JsonPayloadError().as_json()

            kwargs.update(converted_json)
            try:
                return await func(*args, **kwargs)
            except TypeError as e:
                logger.warning(e)
                return BadArguments().as_json()
            except BwServerError as e:
                logger.warning(e)
                return e.as_json()
        else:
            return ExpectedJson().as_json()

    wrapper.__name__ = func.__name__
    return wrapper
