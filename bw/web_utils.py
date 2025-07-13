import logging
import os
import time
from pathlib import Path
from quart import request, render_template_string

from bw.error import ExpectedJson, BadArguments, JsonPayloadError, BwServerError, CacheMiss
from bw.state import State
from bw.events import ServerEvent


logger = logging.getLogger('bw')


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
                    return JsonPayloadError().as_response_code()

            kwargs.update(converted_json)
            try:
                return await func(*args, **kwargs)
            except TypeError as e:
                logger.warning(e)
                return BadArguments().as_response_code()
            except BwServerError as e:
                logger.warning(e)
                return e.as_response_code()
        else:
            return ExpectedJson().as_response_code()

    wrapper.__name__ = func.__name__
    return wrapper


def html_api(*, template_path: Path | str, title: str | None = None, expire_event: ServerEvent | None = None):
    if isinstance(template_path, str):
        template_path = Path(template_path)

    original_template_path = str(template_path)
    page_hash = original_template_path + '--FULL'
    templates_path = Path('./static') / 'templates'

    page_path = templates_path / 'page.html'
    template_path = templates_path / template_path

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # We aggressivley cache the page and template to avoid unnecessary disk reads.
            # If the page or template has changed, we will re-read them and re-render the page.
            try:
                full_page, last_update = State.cache[page_hash]
            except CacheMiss:
                full_page = None
                last_update = 0

            page_update_time = os.path.getmtime(page_path)
            template_update_time = os.path.getmtime(template_path)
            if full_page is None or last_update < page_update_time or last_update < template_update_time:
                try:
                    page, last_update = State.cache['base_page']
                except CacheMiss:
                    page = None
                    last_update = 0

                if page is None or last_update < page_update_time:
                    with open(page_path, encoding='utf-8') as file:
                        page = file.read()
                    State.cache.insert('base_page', (page, page_update_time), expire_event=expire_event)

                try:
                    html, last_update = State.cache[original_template_path]
                except CacheMiss:
                    html = None
                    last_update = 0

                if html is None or last_update < template_update_time:
                    with open(template_path, encoding='utf-8') as file:
                        html = file.read()
                    State.cache.insert(original_template_path, (html, template_update_time), expire_event=expire_event)

                inner_html = await func(html=html, *args, **kwargs)
                full_page = await render_template_string(
                    page,
                    inner_html=inner_html,
                    title=title if title is not None else 'Bourbon Warfare',
                )

                State.cache.insert(page_hash, (full_page, time.time()), expire_event=expire_event)
            return full_page

        wrapper.__name__ = func.__name__
        return wrapper

    return decorator
