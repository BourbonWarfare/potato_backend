import functools
import inspect
import json
import logging
import traceback
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable, Iterable
from inspect import isawaitable
from pathlib import Path
from typing import IO, Any

import aiofiles
from quart import has_request_context, render_template_string, request

from bw.converters import make_json_safe
from bw.error import (
    BadArguments,
    BadHeader,
    BwServerError,
    CannotDetermineSession,
    ExpectedJson,
    JsonPayloadError,
    NeedsAuthenticatedSession,
    SessionExpired,
    WrongAccept,
)
from bw.response import ChunkedResponse, JsonResponse, ServerSentEventResponse, ServerSentResponseError, WebEvent, WebResponse
from bw.web_event import BaseEvent

logger = logging.getLogger('bw.web_utils')


@functools.cache
def _signature(func: Callable[..., Any]) -> inspect.Signature:
    return inspect.signature(func)  # follows __wrapped__ through decorators


def check_call(func: Callable[..., Any], *args: Any, **kwargs: Any) -> inspect.BoundArguments:
    """
    Verify that `func(*args, **kwargs)` matches `func`'s signature without calling it.

    Raises:
        BadArguments: If the arguments don't bind to the signature.

    Returns:
        The bound arguments, in case the caller wants them.
    """
    try:
        return _signature(func).bind(*args, **kwargs)
    except TypeError as e:
        _log_bind_failure(func, e, args, kwargs)
        raise BadArguments() from e


def _log_bind_failure(func: Callable[..., Any], error: TypeError, args: tuple, kwargs: dict) -> None:
    logger.warning(error)
    logger.warning(f'Call to {getattr(func, "__qualname__", func)!r} failed to bind')
    logger.warning(f'Passed args: {args}')
    logger.warning(f'Passed kwargs: {kwargs}')


async def call_checked(func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
    """
    Await `func(*args, **kwargs)`, reporting a call that doesn't match `func`'s signature as `BadArguments`.

    The arguments are checked up front, but a mismatch is only reported if the call actually
    fails. That way the decorators that run first (session, role and permission checks) still
    get to reject the request with their own error, so an unauthorized caller gets 401/403
    rather than a 400 that describes the endpoint's arguments.

    A `TypeError` raised from inside `func`'s body is never caught: when the arguments bind,
    the call is made without any `TypeError` handling, and when they don't, the body never runs.

    Raises:
        BadArguments: If the arguments don't bind and the call fails.
    """
    try:
        _signature(func).bind(*args, **kwargs)
    except TypeError as bind_error:
        try:
            return await func(*args, **kwargs)
        except TypeError as e:
            _log_bind_failure(func, bind_error, args, kwargs)
            raise BadArguments() from e

    return await func(*args, **kwargs)


def hide_parameters[F: Callable[..., Any]](wrapper: F, wrapped: Callable[..., Any], *names: str) -> F:
    """
    Make `wrapper` advertise `wrapped`'s signature minus the parameters the wrapper injects itself.

    Use this in any decorator that supplies arguments to the function it wraps (a session user,
    a header value, a template). Without it, `check_call` follows `__wrapped__` down to the inner
    function and demands arguments the caller was never meant to pass.

    Call it after `functools.wraps`, since `wraps` copies the inner function's `__dict__`
    (including any `__signature__`) onto the wrapper.
    """
    signature = inspect.signature(wrapped)
    wrapper.__signature__ = signature.replace(  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        parameters=[param for param in signature.parameters.values() if param.name not in names]
    )
    return wrapper


def accept_parameters[F: Callable[..., Any]](wrapper: F, wrapped: Callable[..., Any], *names: str) -> F:
    """
    Make `wrapper` advertise `wrapped`'s signature plus optional keyword-only parameters the wrapper consumes.

    The counterpart to `hide_parameters`: use this in any decorator that takes an argument out of
    the call before passing it on (a CSRF token from a form, for example), so `check_call` does not
    reject the call for passing something the inner function doesn't accept.

    Call it after `functools.wraps`.
    """
    signature = inspect.signature(wrapped)
    params = list(signature.parameters.values())

    if any(param.kind is inspect.Parameter.VAR_KEYWORD for param in params):
        # The inner function already accepts anything by keyword
        wrapper.__signature__ = signature  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        return wrapper

    existing = {param.name for param in params}
    params.extend(inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, default=None) for name in names if name not in existing)
    wrapper.__signature__ = signature.replace(parameters=params)  # type: ignore[attr-defined]
    return wrapper


def define_api(func: Callable[..., WebResponse | Awaitable[WebResponse]]):
    """
    ### Decorator for synchronous API functions with error handling

    *Docstring generated by AI.*

    Wraps synchronous API functions to automatically catch and handle BwServerError exceptions,
    converting them into appropriate HTTP responses. Logs warnings for any API errors
    and ensures consistent error response formatting across all synchronous API endpoints.

    **Async:** No

    **Args:**
    - `func` (`Callable[..., WebResponse]`): The API function to wrap with error handling.

    **Returns:**
    - `Callable[..., WebResponse | Awaitable[WebResponse]]`: A wrapped function that may raise an instance of `BwServerError`.

    **Example:**
    ```python
    @define_api
    def my_sync_api_function() -> WebResponse:
        return Ok()
    # Callable[..., WebResponse]

    @define_api
    async def my_async_api_function() -> WebResponse:
        return Ok()
    # Callable[..., Awaitable[WebResponse]]
    ```
    """

    def handle_exception(exception: BwServerError) -> WebResponse:
        logger.warning(f'API error: {exception}')
        logger.debug(f'Exception traceback:\n{traceback.format_exc()}')

        response = exception.as_response_code()
        logger.debug(f'status: {response.status}')
        return response

    async def async_handle_exception(exception: BwServerError) -> WebResponse:
        return handle_exception(exception)

    async def asyncfunc(*args, **kwargs) -> WebResponse:
        try:
            value = func(*args, **kwargs)
            assert isawaitable(value)
            awaited_value = await value
            assert isinstance(awaited_value, WebResponse)
            return awaited_value
        except BwServerError as e:
            return await async_handle_exception(e)

    def syncfunc(*args, **kwargs) -> WebResponse:
        try:
            value = func(*args, **kwargs)
            assert isinstance(value, WebResponse)
            return value
        except BwServerError as e:
            return handle_exception(e)

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> WebResponse | Awaitable[WebResponse]:
        if inspect.iscoroutinefunction(func):
            return asyncfunc(*args, **kwargs)
        else:
            return syncfunc(*args, **kwargs)

    return wrapper


def url_endpoint(func: Callable[..., Awaitable[WebResponse]]):
    """
    ### Decorator for URL endpoint functions with error handling

    *Docstring generated by AI.*

    Wraps URL endpoint functions to automatically catch and handle BwServerError exceptions,
    converting them into appropriate HTTP responses. Provides error handling specifically
    for URL-based endpoints with appropriate logging for debugging URL API issues.

    **Async:** No (decorator function itself is synchronous)

    **Args:**
    - `func` (`Callable[..., Awaitable[WebResponse]]`): The URL endpoint function to wrap with error handling.

    **Returns:**
    - `Callable[..., Awaitable[WebResponse]]`: A wrapped function that handles BwServerError exceptions for URL endpoints.

    **Example:**
    ```python
    @url_endpoint
    async def my_url_endpoint() -> WebResponse:
        return Ok()
    # Callable[..., Awaitable[WebResponse]]
    ```
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await call_checked(func, *args, **kwargs)
        except BwServerError as e:
            logger.warning(f'Error in URL API: {e}')
            return e.as_response_code()

    return wrapper


def form_endpoint(func: Callable[..., Awaitable[WebResponse]]):
    """
    ### Decorator for endpoint functions which are called from an HTML form, with error handling

    *Docstring generated by AI.*

    Wraps endpoint functions from forms to automatically catch and handle BwServerError exceptions,
    converting them into appropriate HTTP responses. Provides error handling specifically
    for URL-based endpoints with appropriate logging for debugging URL API issues.

    Form values are also converted into kwargs

    **Async:** No (decorator function itself is synchronous)

    **Args:**
    - `func` (`Callable[..., Awaitable[WebResponse]]`): The endpoint function to wrap with error handling.

    **Returns:**
    - `Callable[..., Awaitable[WebResponse]]`: A wrapped function that handles BwServerError exceptions for endpoints.

    **Example:**
    ```python
    @form_endpoint
    async def my_form_endpoint(value1: str, value2: int) -> WebResponse:
        return Ok()
    # Callable[..., Awaitable[WebResponse]]
    ```
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        form_values = await request.form
        kwargs.update(form_values)
        kwargs = {key.replace('-', '_'): value for key, value in kwargs.items()}
        try:
            return await call_checked(func, *args, **kwargs)
        except BwServerError as e:
            logger.warning(f'Error in form API: {e}')
            return e.as_response_code()

    return wrapper


def json_endpoint(func: Callable[..., Awaitable[JsonResponse]]):
    """
    ### Decorator for JSON endpoint functions with request parsing and error handling

    *Docstring generated by AI.*

    Wraps JSON endpoint functions to automatically parse JSON request data and merge it with
    function arguments. Handles JSON parsing errors, duplicate key conflicts, type errors,
    and BwServerError exceptions. Ensures all JSON endpoints receive properly parsed data
    and return consistent error responses for malformed requests.

    **Async:** No (decorator function itself is synchronous)

    **Args:**
    - `func` (`Callable[..., Awaitable[JsonResponse]]`): The JSON endpoint function to wrap with request parsing and error
    handling.

    **Raises:**
    - `JsonPayloadError`: When duplicate keys are found between request JSON and function arguments.
    - `BadArguments`: When function arguments don't match the expected signature.
    - `ExpectedJson`: When no JSON payload is provided in the request.

    **Returns:**
    - `Callable[..., Awaitable[JsonResponse]]`: A wrapped function that parses JSON requests and handles errors.

    **Example:**
    ```python
    @json_endpoint
    async def my_json_endpoint(name: str) -> JsonResponse:
        return JsonResponse({'message': f'Hello {name}'})
    # Callable[..., Awaitable[JsonResponse]]
    ```
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        converted_json = await request.get_json()
        if converted_json is None:
            logger.warning('Endpoint expects Json')
            return ExpectedJson().as_response_code()

        if not isinstance(converted_json, dict):
            logger.warning('Json payload must be an object')
            return BadArguments().as_response_code()

        for key in converted_json:
            if key in kwargs:
                logger.warning(f'Duplicate key found while parsing arguments: {key}')
                return JsonPayloadError().as_response_code()

        kwargs.update(converted_json)

        try:
            return await call_checked(func, *args, **kwargs)
        except BwServerError as e:
            logger.warning(e)
            return e.as_response_code()

    return wrapper


async def load_template_from_disk(*, template_path: Path | str, base_path: str = 'templates') -> str:
    if isinstance(template_path, str):
        template_path = Path(template_path)
    templates_path = Path('./static') / base_path
    template_path = templates_path / template_path
    async with aiofiles.open(template_path, encoding='utf-8') as file:
        return await file.read()


def is_htmx_request() -> bool:
    if not has_request_context():
        return False
    return request.headers.get('HX-Request', '').lower() == 'true' or 'HX-Request' in request.headers


def is_htmx_partial_request() -> bool:
    """Return True when HTMX is asking for a fragment rather than a full document.

    HTMX 4 adds HX-Request-Type and hx-boost sends HX-Boosted. Treat those full-page
    navigation requests like normal browser navigation so we render the complete shell.
    """
    if not is_htmx_request():
        return False
    request_type = request.headers.get('HX-Request-Type', '').lower()
    boosted = request.headers.get('HX-Boosted', '').lower() == 'true'
    return request_type != 'full' and not boosted


def htmx_headers(
    *,
    retarget: str | None = None,
    reswap: str | None = None,
    redirect: str | None = None,
    location: str | None = None,
    push_url: str | None = None,
    replace_url: str | None = None,
    trigger: str | dict[str, Any] | None = None,
) -> dict[str, str]:
    headers = {}
    if retarget is not None:
        headers['HX-Retarget'] = retarget
    if reswap is not None:
        headers['HX-Reswap'] = reswap
    if redirect is not None:
        headers['HX-Redirect'] = redirect
    if location is not None:
        headers['HX-Location'] = location
    if push_url is not None:
        headers['HX-Push-Url'] = push_url
    if replace_url is not None:
        headers['HX-Replace-Url'] = replace_url
    if trigger is not None:
        headers['HX-Trigger'] = json.dumps(trigger) if isinstance(trigger, dict) else trigger
    return headers


def htmx_response(
    html: str,
    *,
    retarget: str | None = None,
    reswap: str | None = None,
    trigger: str | dict[str, Any] | None = None,
    headers: dict[str, Any] | None = None,
    mimetype: str = 'text/html',
) -> ChunkedResponse:
    response_headers = dict(headers or {})
    response_headers.update(htmx_headers(retarget=retarget, reswap=reswap, trigger=trigger))
    return chunk_text_response(html, mimetype=mimetype, headers=response_headers)


async def htmx_template_response(
    template_path: Path | str,
    *,
    context: dict[str, Any] | None = None,
    retarget: str | None = None,
    reswap: str | None = None,
    trigger: str | dict[str, Any] | None = None,
    headers: dict[str, Any] | None = None,
) -> ChunkedResponse:
    html = await load_template_from_disk(template_path=template_path)
    rendered = await render_template_string(html, **(context or {}))
    return htmx_response(rendered, retarget=retarget, reswap=reswap, trigger=trigger, headers=headers)


def htmx_redirect(location: str, *, status: int = 303) -> WebResponse:
    """Return a redirect response that works for both HTMX and regular form submissions.

    HTMX intentionally ignores response headers on 3xx responses, so HX-Redirect must be
    sent on a non-redirect status. Regular browser submissions still need a Location header
    with a 3xx status.
    """
    if is_htmx_request():
        return WebResponse(status=204, headers=htmx_headers(redirect=location))
    return WebResponse(status=status, headers={'Location': location})


def html_endpoint(
    *,
    template_path: Path | str,
    title: str | None = None,
    return_partial: bool = False,
    mimetype: str = 'text/html',
    injected_headers: list[str] | None = None,
    injected_response_headers: dict[str, str] | None = None,
):
    """
    ### Decorator for HTML endpoint functions with template caching and rendering

    *Docstring generated by AI.*

    Wraps HTML endpoint functions to provide automatic template loading, caching, and rendering.
    Renders the final page by injecting function output into the base page template.

    **Async:** No (decorator function itself is synchronous)

    **Args:**
    - `template_path` (`Path | str`): The path to the HTML template file relative to the templates directory.
    - `title` (`str | None`): The page title to use in the rendered template. Defaults to 'Bourbon Warfare'.

    **Returns:**
    - `Callable`: A decorator function that wraps HTML endpoint functions with template rendering capabilities.

    **Example:**
    ```python
    @html_endpoint(template_path='dashboard.html', title='Dashboard')
    async def dashboard_page(html: str) -> str:
        return render_template_string(html, data={'status': 'active'})
    # Callable[..., Awaitable[str]]
    ```
    """
    from bw.auth.api import AuthApi
    from bw.auth.session import SessionStore
    from bw.auth.user import UserStore
    from bw.auth.validators import validate_session
    from bw.navigation import visible_nav_links
    from bw.state import State

    if isinstance(template_path, str):
        template_path = Path(template_path)

    def decorator(func: Callable[..., Awaitable[str | WebResponse]]):
        signature = inspect.signature(func)
        logged_in_parameter = signature.parameters.get('logged_in')
        inject_logged_in = logged_in_parameter is not None and logged_in_parameter.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if mimetype == 'text/xml':
                html = await load_template_from_disk(template_path=template_path, base_path='xml')
            else:
                html = await load_template_from_disk(template_path=template_path)
            kwargs['html'] = html

            def session_template_context() -> dict[str, Any]:
                try:
                    session_token = AuthApi().get_session_cookie()
                    validate_session(State.state, session_token)
                    user = SessionStore().get_user_from_session_token(State.state, session_token=session_token)
                except (CannotDetermineSession, SessionExpired, NeedsAuthenticatedSession):
                    return {'logged_in': False, 'role_grants': None, 'nav_links': []}

                role_grants = UserStore().get_users_role(State.state, user)
                return {'logged_in': True, 'role_grants': role_grants, 'nav_links': visible_nav_links(role_grants)}

            template_context = session_template_context()
            is_logged_in = template_context['logged_in']

            if inject_logged_in:
                kwargs['logged_in'] = is_logged_in

            error_status: int | None = None
            try:
                inner_html = await func(*args, **kwargs)
            except BwServerError as e:
                logger.warning(e)
                error_status = e.status()
                try:
                    inner_html = await load_template_from_disk(template_path=Path('error') / f'{error_status}.html')
                except FileNotFoundError:
                    inner_html = f'<h1>{error_status}</h1><p>{e!s}</p>'

            response_headers = injected_response_headers if injected_response_headers else {}

            def respond(body: str) -> ChunkedResponse:
                response = chunk_text_response(body, mimetype=mimetype, headers=response_headers)
                if error_status is not None:
                    response.status_code = error_status
                return response

            # The endpoint may mutate the session (OAuth login, logout redirects, etc.).
            # Recompute before rendering the full shell so the navbar is not stale.
            template_context = session_template_context()
            is_logged_in = template_context['logged_in']

            if is_htmx_partial_request() or return_partial:
                return respond(inner_html) if isinstance(inner_html, str) else inner_html

            partial_page = await load_template_from_disk(template_path='page.html')
            full_page = await render_template_string(
                partial_page,
                inner_html=inner_html,
                title=title if title is not None else 'Bourbon Warfare',
                logged_in=is_logged_in,
                nav_links=template_context['nav_links'],
                role_grants=template_context['role_grants'],
                injected_headers=injected_headers if injected_headers else [],
            )

            return respond(full_page) if isinstance(inner_html, str) else inner_html

        injected = ('html', 'logged_in') if inject_logged_in else ('html',)
        return hide_parameters(wrapper, func, *injected)

    return decorator


def sse_endpoint(func: Callable[..., AsyncIterator[WebEvent | BaseEvent]]):
    """
    ### Decorator for Server-Sent Events endpoint functions

    *Docstring generated by AI.*

    Wraps SSE endpoint functions to automatically convert async generators into proper
    ServerSentEventResponse objects. Handles conversion of BaseEvent objects to WebEvent
    format for proper SSE transmission. Ensures all SSE endpoints return compatible
    response objects for real-time event streaming.

    **Async:** No (decorator function itself is synchronous)

    **Args:**
    - `func` (`Callable[..., AsyncIterator[WebEvent | BaseEvent]]`): The SSE endpoint function that yields events.

    **Returns:**
    - `Callable[..., Awaitable[ServerSentEventResponse]]`: A wrapped function that returns a proper SSE response.

    **Example:**
    ```python
    @sse_endpoint
    async def event_stream():
        yield WebEvent('message', {'data': 'Hello'})
    # Callable[..., Awaitable[ServerSentEventResponse]]
    ```
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> ServerSentEventResponse:
        if 'text/event-stream' not in request.accept_mimetypes:
            exception = WrongAccept(recieved=', '.join(request.accept_mimetypes.values()), expected='text/event-stream')
            logger.error(f'Cannot connect SSE socket: {exception!s}')
            return ServerSentResponseError(exception.status())

        async def async_byte_generator() -> AsyncGenerator[bytes]:
            async for event in func(*args, **kwargs):
                yield event.encode()

        return ServerSentEventResponse.from_async_generator(async_byte_generator)

    return wrapper


def unwrap_headers(*headers: tuple[str, Any]):
    """
    ### Decorator to unwrap headers into the function parameters

    Extracts headers from the body to give as parameters for the wrapped function

    **Async:** No (decorator function itself is synchronous)

    **Args:**
    - `headers` (`tuple[str, type]`): The headers and their expected types.

    **Example:**
    ```python
    @unwrap_headers(('foo': int))
    def event_stream(foo: int):
        print(foo)
    ```
    """

    def transform(input: str) -> str:
        input = input.replace('-', '_')
        return input.lower()

    def decorator(func: Callable[..., Awaitable[str]]):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for header, header_type in headers:
                try:
                    if header not in request.headers:
                        raise KeyError(header, request.headers)
                    kwargs[transform(header)] = header_type(request.headers.get(header))
                except (TypeError, KeyError):
                    raise BadHeader()
            return await func(*args, **kwargs)

        return hide_parameters(wrapper, func, *(transform(header) for header, _ in headers))

    return decorator


def chunk_text_response(
    to_stream: str, *, max_chunk_size: int = 2**10, headers: dict[str, Any] | None = None, mimetype: str | None = None
) -> ChunkedResponse:
    async def chunk_generator():
        to_stream_bin = to_stream.encode('utf-8')
        for idx in range(0, len(to_stream_bin), max_chunk_size):
            yield to_stream_bin[idx : idx + max_chunk_size]

    return ChunkedResponse.from_async_generator(mimetype if mimetype else 'text/plain', chunk_generator, headers=headers)


def chunk_json_response(
    to_stream: Iterable[dict[str, Any]], *, max_chunk_size: int = 2**10, headers: dict[str, Any] | None = None
) -> ChunkedResponse:
    async def chunk_generator():
        response_buffer: bytes = b''

        for response in to_stream:
            response_bytes = (json.dumps(make_json_safe(response)) + '\n').encode('utf-8')

            if len(response_bytes) >= max_chunk_size:
                # Push the rows before us to maintain order
                if len(response_buffer) > 0:
                    yield response_buffer
                    response_buffer = b''
                yield response_bytes
            else:
                response_buffer += response_bytes
                if len(response_buffer) >= max_chunk_size:
                    yield response_buffer
                    response_buffer = b''

        if response_buffer:
            yield response_buffer

    return ChunkedResponse.from_async_generator('application/x-ndjson', chunk_generator, headers=headers)


def chunk_file_response(
    file_obj: IO, *, chunk_size: int = 2**10, headers: dict[str, Any] | None = None, mimetype: str | None = None
) -> ChunkedResponse:
    async def read_file(file_obj: IO, chunk_size: int) -> str | bytes:
        if inspect.iscoroutinefunction(file_obj.read):
            return await file_obj.read(chunk_size)
        else:
            return file_obj.read(chunk_size)

    async def chunk_generator():
        try:
            while chunk := await read_file(file_obj, chunk_size):
                if isinstance(chunk, str):
                    yield chunk.encode('utf-8')
                else:
                    yield chunk
        finally:
            if not file_obj.closed:
                # Safely closes the file when the stream ends or aborts
                if inspect.iscoroutinefunction(file_obj.close):
                    await file_obj.close()
                else:
                    file_obj.close()

    return ChunkedResponse.from_async_generator(mimetype if mimetype else 'text/plain', chunk_generator, headers=headers)
