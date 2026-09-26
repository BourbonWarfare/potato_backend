import functools
import inspect
import io
from contextlib import aclosing
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from bw.error import BadArguments, BadHeader, BwServerError
from bw.response import JsonResponse, WebResponse
from bw.web_utils import (
    accept_parameters,
    call_checked,
    check_call,
    chunk_file_response,
    chunk_json_response,
    chunk_text_response,
    define_api,
    form_endpoint,
    hide_parameters,
    html_endpoint,
    htmx_headers,
    htmx_redirect,
    htmx_response,
    htmx_template_response,
    is_htmx_partial_request,
    json_endpoint,
    sse_endpoint,
    unwrap_headers,
    url_endpoint,
)

# ==============================================================================
# FIXTURES & MOCKS
# ==============================================================================


class AwaitableForm:
    def __init__(self, values: dict[str, Any] | None = None):
        self.values = values or {}

    def __await__(self):
        async def _form():
            return self.values

        return _form().__await__()


@pytest.fixture
def mock_request(mocker):
    """Mocks the quart.request context object."""
    request_mock = MagicMock()
    # Async mock for get_json()
    request_mock.get_json = AsyncMock(return_value=None)
    request_mock.headers = {}
    request_mock.accept_mimetypes = {'text/event-stream': 'text/event-stream'}
    request_mock.form = AwaitableForm()

    mocker.patch('bw.web_utils.request', request_mock)
    return request_mock


@pytest.fixture
def mock_render_template(mocker):
    """Mocks Quart's render_template_string."""
    return mocker.patch('bw.web_utils.render_template_string', new_callable=AsyncMock)


# Mock Response Classes to easily assert returns


class MockWebResponse(WebResponse):
    def __init__(self):
        pass


class MockJsonResponse(JsonResponse):
    def __init__(self):
        pass


class MockErrorResponse(WebResponse):
    def __init__(self):
        self._status = '500 INTERNAL SERVER ERROR'


@pytest.fixture
def mock_error():
    """Provides a dummy BwServerError that returns a predictable response."""

    class DummyError(BwServerError):
        def __init__(self):
            # Store the response so it returns the exact same instance every time
            self.expected_response = MockErrorResponse()

        def as_response_code(self):
            return self.expected_response

        def status(self):
            return 500

    return DummyError()


def passthrough(func):
    """
    A decorator whose wrapper accepts any arguments, hiding the real signature at call time.

    Stacking this under an endpoint decorator reproduces the case where a bad call only
    fails once the coroutine is awaited, not when it is created.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)

    return wrapper


# ==============================================================================
# UNIT UNDER TEST: check_call
# ==============================================================================


def test__check_call__returns_bound_arguments_for_valid_call():
    def func(a: int, b: str = 'x'):
        pass

    bound = check_call(func, 1, b='y')

    assert isinstance(bound, inspect.BoundArguments)
    assert bound.arguments == {'a': 1, 'b': 'y'}


def test__check_call__raises_bad_arguments_on_missing_argument():
    def func(a: int, b: str):
        pass

    with pytest.raises(BadArguments):
        check_call(func, 1)


def test__check_call__raises_bad_arguments_on_unexpected_keyword():
    def func(a: int):
        pass

    with pytest.raises(BadArguments):
        check_call(func, a=1, extra=2)


def test__check_call__raises_bad_arguments_on_too_many_positional():
    def func(a: int):
        pass

    with pytest.raises(BadArguments):
        check_call(func, 1, 2)


def test__check_call__bad_arguments_chains_original_type_error():
    def func(a: int):
        pass

    with pytest.raises(BadArguments) as exc_info:
        check_call(func)

    assert isinstance(exc_info.value.__cause__, TypeError)


def test__check_call__does_not_call_function():
    calls = []

    def func(a: int):
        calls.append(a)

    check_call(func, 1)

    assert calls == []


def test__check_call__accepts_anything_for_var_keyword_function():
    def func(**kwargs):
        pass

    check_call(func, anything=1, at_all=2)


def test__check_call__follows_wrapped_signature_through_decorators():
    @passthrough
    async def func(a: int):
        pass

    # The outer wrapper takes *args/**kwargs, but check_call must use the real signature
    with pytest.raises(BadArguments):
        check_call(func, not_a=1)


def injects_user(func):
    """A decorator that supplies `session_user` itself, like `require_session`."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await func('the-user', *args, **kwargs)

    return hide_parameters(wrapper, func, 'session_user')


def test__hide_parameters__removes_injected_parameter_from_signature():
    @injects_user
    async def func(session_user: str, a: int):
        pass

    assert list(inspect.signature(func).parameters) == ['a']


def test__check_call__does_not_require_injected_parameter():
    @injects_user
    async def func(session_user: str, a: int):
        pass

    check_call(func, a=1)


def test__check_call__rejects_injected_parameter_passed_by_caller():
    @injects_user
    async def func(session_user: str, a: int):
        pass

    with pytest.raises(BadArguments):
        check_call(func, session_user='spoofed', a=1)


def test__check_call__hidden_parameters_survive_further_wrapping():
    @passthrough
    @injects_user
    async def func(session_user: str, a: int):
        pass

    check_call(func, a=1)
    with pytest.raises(BadArguments):
        check_call(func)


def consumes_token(func):
    """A decorator that strips `csrf_token` out of the call, like `verify_csrf_from_form`."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        kwargs.pop('csrf_token', None)
        return await func(*args, **kwargs)

    return accept_parameters(wrapper, func, 'csrf_token')


def test__accept_parameters__adds_optional_keyword_parameter():
    @consumes_token
    async def func(a: int):
        pass

    params = inspect.signature(func).parameters
    assert list(params) == ['a', 'csrf_token']
    assert params['csrf_token'].kind is inspect.Parameter.KEYWORD_ONLY
    assert params['csrf_token'].default is None


def test__accept_parameters__leaves_var_keyword_signature_alone():
    @consumes_token
    async def func(a: int, **kwargs):
        pass

    assert list(inspect.signature(func).parameters) == ['a', 'kwargs']


def test__check_call__allows_consumed_parameter_with_or_without_it():
    @consumes_token
    async def func(a: int):
        pass

    check_call(func, a=1)
    check_call(func, a=1, csrf_token='abc')
    with pytest.raises(BadArguments):
        check_call(func, a=1, other='abc')


@pytest.mark.asyncio
async def test__form_endpoint__consumed_form_value_is_not_rejected(mock_request):
    expected = MockWebResponse()

    @form_endpoint
    @consumes_token
    async def endpoint(a: str):
        return expected

    mock_request.form = AwaitableForm({'a': 'x', 'csrf_token': 'abc'})
    assert await endpoint() is expected


@pytest.mark.asyncio
async def test__json_endpoint__injecting_decorator_is_not_treated_as_missing_argument(mock_request):
    mock_request.get_json.return_value = {'a': 1}
    expected = MockJsonResponse()

    @json_endpoint
    @injects_user
    async def endpoint(session_user: str, a: int):
        assert session_user == 'the-user'
        assert a == 1
        return expected

    assert await endpoint() is expected


def rejects_request(error: BwServerError):
    """A decorator that injects `session_user` but rejects every request first, like a failing `require_session`."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            raise error

        return hide_parameters(wrapper, func, 'session_user')

    return decorator


@pytest.mark.asyncio
async def test__call_checked__raises_bad_arguments_when_call_fails():
    async def func(a: int):
        pass

    with pytest.raises(BadArguments):
        await call_checked(func, b=1)


@pytest.mark.asyncio
async def test__call_checked__type_error_in_body_is_not_caught():
    async def func(a: int):
        raise TypeError('from the body')

    with pytest.raises(TypeError, match='from the body'):
        await call_checked(func, a=1)


@pytest.mark.asyncio
async def test__call_checked__decorator_error_wins_over_bad_arguments(mock_error):
    @rejects_request(mock_error)
    async def func(session_user: str, event: str):
        pass

    with pytest.raises(type(mock_error)):
        await call_checked(func)


@pytest.mark.asyncio
async def test__call_checked__does_not_log_bad_arguments_when_decorator_rejects(mock_error, caplog):
    @rejects_request(mock_error)
    async def func(session_user: str, event: str):
        pass

    with pytest.raises(type(mock_error)):
        await call_checked(func)

    assert 'failed to bind' not in caplog.text


@pytest.mark.asyncio
async def test__url_endpoint__rejecting_decorator_wins_over_bad_arguments(mock_request, mock_error):
    @url_endpoint
    @rejects_request(mock_error)
    async def endpoint(session_user: str, event: str):
        pass

    assert await endpoint() is mock_error.as_response_code()


@pytest.mark.asyncio
async def test__form_endpoint__rejecting_decorator_wins_over_bad_arguments(mock_request, mock_error):
    @form_endpoint
    @rejects_request(mock_error)
    async def endpoint(session_user: str, event: str):
        pass

    assert await endpoint() is mock_error.as_response_code()


@pytest.mark.asyncio
async def test__json_endpoint__rejecting_decorator_wins_over_bad_arguments(mock_request, mock_error):
    mock_request.get_json.return_value = {}

    @json_endpoint
    @rejects_request(mock_error)
    async def endpoint(session_user: str, event: str):
        pass

    assert await endpoint() is mock_error.as_response_code()


@pytest.mark.asyncio
async def test__json_endpoint__bad_arguments_after_passing_decorator_return_bad_request(mock_request):
    mock_request.get_json.return_value = {}

    @json_endpoint
    @injects_user
    async def endpoint(session_user: str, event: str):
        pass

    response = await endpoint()
    assert response.status == '400 BAD REQUEST'


@pytest.mark.asyncio
async def test__json_endpoint__unwrap_headers_parameters_are_not_required_from_payload(mock_request):
    mock_request.get_json.return_value = {'a': 1}
    mock_request.headers = {'X-Api-Version': '2'}
    expected = MockJsonResponse()

    @json_endpoint
    @unwrap_headers(('X-Api-Version', int))
    async def endpoint(x_api_version: int, a: int):
        assert x_api_version == 2
        return expected

    assert await endpoint() is expected


# ==============================================================================
# UNIT UNDER TEST: define_api
# ==============================================================================


def test__define_api__sync_returns_expected_response():
    expected = MockWebResponse()

    @define_api
    def sync_endpoint():
        return expected

    assert sync_endpoint() is expected


@pytest.mark.asyncio
async def test__define_api__async_returns_expected_response():
    expected = MockWebResponse()

    @define_api
    async def async_endpoint():
        return expected

    assert await async_endpoint() is expected


def test__define_api__sync_catches_bw_server_error(mock_error):
    @define_api
    def failing_sync():
        raise mock_error

    response = failing_sync()
    assert isinstance(response, MockErrorResponse)


@pytest.mark.asyncio
async def test__define_api__async_catches_bw_server_error(mock_error):
    @define_api
    async def failing_async():
        raise mock_error

    response = await failing_async()
    assert isinstance(response, MockErrorResponse)


# ==============================================================================
# UNIT UNDER TEST: url_endpoint
# ==============================================================================


@pytest.mark.asyncio
async def test__url_endpoint__returns_expected_response():
    expected = MockWebResponse()

    @url_endpoint
    async def endpoint():
        return expected

    assert await endpoint() is expected


@pytest.mark.asyncio
async def test__url_endpoint__catches_bw_server_error(mock_error):
    @url_endpoint
    async def endpoint():
        raise mock_error

    response = await endpoint()
    assert isinstance(response, MockErrorResponse)


@pytest.mark.asyncio
async def test__url_endpoint__type_error_in_function_is_not_caught(mock_request):
    @url_endpoint
    async def endpoint():
        raise TypeError()

    with pytest.raises(TypeError):
        await endpoint()


@pytest.mark.asyncio
async def test__url_endpoint__bad_arguments_return_bad_request(mock_request, mock_error):
    @url_endpoint
    async def endpoint(my_arg: int):
        return 'blah'

    response = await endpoint(fake=400)
    assert response.status == '400 BAD REQUEST'


@pytest.mark.asyncio
async def test__url_endpoint__bad_arguments_through_stacked_decorator_return_bad_request(mock_request):
    @url_endpoint
    @passthrough
    async def endpoint(my_arg: int):
        return 'blah'

    response = await endpoint(fake=400)
    assert response.status == '400 BAD REQUEST'


@pytest.mark.asyncio
async def test__url_endpoint__type_error_through_stacked_decorator_is_not_caught(mock_request):
    @url_endpoint
    @passthrough
    async def endpoint(my_arg: int):
        raise TypeError()

    with pytest.raises(TypeError):
        await endpoint(my_arg=1)


# ==============================================================================
# UNIT UNDER TEST: form_endpoint
# ==============================================================================


@pytest.mark.asyncio
async def test__form_endpoint__returns_expected_response(mock_request):
    expected = MockWebResponse()

    @form_endpoint
    async def endpoint():
        return expected

    assert await endpoint() is expected


@pytest.mark.asyncio
async def test__form_endpoint__catches_bw_server_error(mock_error, mock_request):
    @form_endpoint
    async def endpoint():
        raise mock_error

    response = await endpoint()
    assert isinstance(response, MockErrorResponse)


@pytest.mark.asyncio
async def test__form_endpoint__type_error_in_function_is_not_caught(mock_request):
    @form_endpoint
    async def endpoint():
        raise TypeError()

    with pytest.raises(TypeError):
        await endpoint()


@pytest.mark.asyncio
async def test__form_endpoint__form_values_are_inserted(mock_request, mock_error):
    expected = MockWebResponse()

    @form_endpoint
    async def endpoint(arg1: int, arg2: str):
        assert arg1 == 52
        assert arg2 == 'blah'
        return expected

    mock_request.form = AwaitableForm({'arg1': 52, 'arg2': 'blah'})
    response = await endpoint()
    assert response == expected


@pytest.mark.asyncio
async def test__form_endpoint__hyphenated_form_keys_become_underscored(mock_request):
    expected = MockWebResponse()

    @form_endpoint
    async def endpoint(first_name: str):
        assert first_name == 'Alice'
        return expected

    mock_request.form = AwaitableForm({'first-name': 'Alice'})
    assert await endpoint() is expected


@pytest.mark.asyncio
async def test__form_endpoint__missing_arg_type_error(mock_request, mock_error):
    @form_endpoint
    async def endpoint(arg1: int, arg2: str, arg3: Any):
        pass

    mock_request.form = AwaitableForm({'arg1': 52, 'arg2': 'blah'})
    response = await endpoint()
    assert response.status == '400 BAD REQUEST'


@pytest.mark.asyncio
async def test__form_endpoint__bad_arguments_return_bad_request(mock_request, mock_error):
    @form_endpoint
    async def endpoint(my_arg: int):
        return 'blah'

    response = await endpoint(fake=400)
    assert response.status == '400 BAD REQUEST'


@pytest.mark.asyncio
async def test__form_endpoint__bad_arguments_through_stacked_decorator_return_bad_request(mock_request):
    @form_endpoint
    @passthrough
    async def endpoint(my_arg: int):
        return 'blah'

    mock_request.form = AwaitableForm({'not_real_arg': 'blah'})
    response = await endpoint()
    assert response.status == '400 BAD REQUEST'


@pytest.mark.asyncio
async def test__form_endpoint__type_error_through_stacked_decorator_is_not_caught(mock_request):
    @form_endpoint
    @passthrough
    async def endpoint(my_arg: int):
        raise TypeError()

    mock_request.form = AwaitableForm({'my_arg': 1})
    with pytest.raises(TypeError):
        await endpoint()


# ==============================================================================
# UNIT UNDER TEST: json_endpoint
# ==============================================================================


@pytest.mark.asyncio
async def test__json_endpoint__merges_json_with_kwargs(mock_request):
    mock_request.get_json.return_value = {'age': 30}

    @json_endpoint
    async def endpoint(name: str, age: int):
        return MockJsonResponse()

    # 'name' comes from kwargs/routing, 'age' comes from JSON body
    await endpoint(name='Alice')
    # If no exceptions were raised, the behavior is correct.


@pytest.mark.asyncio
async def test__json_endpoint__returns_expected_json_when_no_payload(mock_request, mocker):
    mock_request.get_json.return_value = None
    expected_error_response = MockErrorResponse()
    mocker.patch('bw.error.ExpectedJson.as_response_code', return_value=expected_error_response)

    @json_endpoint
    async def endpoint():
        return MockJsonResponse()

    assert await endpoint() is expected_error_response


@pytest.mark.asyncio
async def test__json_endpoint__returns_json_payload_error_on_duplicate_keys(mock_request, mocker):
    mock_request.get_json.return_value = {'id': 2}  # Clashes with kwarg "id"
    expected_error_response = MockErrorResponse()
    mocker.patch('bw.error.JsonPayloadError.as_response_code', return_value=expected_error_response)

    @json_endpoint
    async def endpoint(id: int):
        return MockJsonResponse()

    assert await endpoint(id=1) is expected_error_response


@pytest.mark.asyncio
async def test__json_endpoint__returns_bad_arguments_on_type_error(mock_request, mocker):
    mock_request.get_json.return_value = {'extra_arg': 'whoops'}
    expected_error_response = MockErrorResponse()
    mocker.patch('bw.error.BadArguments.as_response_code', return_value=expected_error_response)

    @json_endpoint
    async def endpoint(required: str):
        # This will raise TypeError internally because `extra_arg` is passed but not expected
        pass

    assert await endpoint(required='test') is expected_error_response


@pytest.mark.asyncio
async def test__json_endpoint__catches_bw_server_error(mock_request, mock_error):
    mock_request.get_json.return_value = {}

    @json_endpoint
    async def endpoint():
        raise mock_error

    assert await endpoint() is mock_error.as_response_code()


@pytest.mark.asyncio
async def test__json_endpoint__type_error_in_function_is_not_caught(mock_request):
    mock_request.get_json.return_value = {}

    @json_endpoint
    async def endpoint():
        raise TypeError()

    with pytest.raises(TypeError):
        await endpoint()


@pytest.mark.asyncio
async def test__json_endpoint__bad_arguments_return_bad_request(mock_request, mock_error):
    mock_request.get_json.return_value = {'not_real_arg': 'blah'}

    @json_endpoint
    async def endpoint(my_arg: int):
        return {}

    response = await endpoint()
    assert response.status == '400 BAD REQUEST'


@pytest.mark.asyncio
async def test__json_endpoint__bad_arguments_through_stacked_decorator_return_bad_request(mock_request):
    mock_request.get_json.return_value = {'not_real_arg': 'blah'}

    @json_endpoint
    @passthrough
    async def endpoint(my_arg: int):
        return {}

    response = await endpoint()
    assert response.status == '400 BAD REQUEST'


@pytest.mark.asyncio
async def test__json_endpoint__type_error_through_stacked_decorator_is_not_caught(mock_request):
    mock_request.get_json.return_value = {'my_arg': 1}

    @json_endpoint
    @passthrough
    async def endpoint(my_arg: int):
        raise TypeError()

    with pytest.raises(TypeError):
        await endpoint()


@pytest.mark.asyncio
@pytest.mark.parametrize('payload', [['a', 'b'], 'a string', 42, True])
async def test__json_endpoint__non_object_payload_returns_bad_request(mock_request, payload):
    mock_request.get_json.return_value = payload

    @json_endpoint
    async def endpoint():
        return MockJsonResponse()

    response = await endpoint()
    assert response.status == '400 BAD REQUEST'


@pytest.mark.asyncio
async def test__json_endpoint__empty_object_payload_is_accepted(mock_request):
    mock_request.get_json.return_value = {}
    expected = MockJsonResponse()

    @json_endpoint
    async def endpoint():
        return expected

    assert await endpoint() is expected


# ==============================================================================
# UNIT UNDER TEST: htmx helpers
# ==============================================================================


def test__htmx_headers__builds_common_response_headers():
    headers = htmx_headers(retarget='#card', reswap='outerHTML', trigger={'saved': True}, push_url='/next')

    assert headers == {
        'HX-Retarget': '#card',
        'HX-Reswap': 'outerHTML',
        'HX-Trigger': '{"saved": true}',
        'HX-Push-Url': '/next',
    }


@pytest.mark.asyncio
async def test__htmx_response__returns_html_with_headers():
    response = htmx_response('<p>Saved</p>', retarget='#status', reswap='innerHTML')
    body = b''.join(await consume_generator(response)).decode()

    assert body == '<p>Saved</p>'
    assert response.media_type == 'text/html'
    assert response.headers['HX-Retarget'] == '#status'
    assert response.headers['HX-Reswap'] == 'innerHTML'


@pytest.mark.asyncio
async def test__htmx_template_response__renders_template_and_headers(mocker, mock_render_template):
    mocker.patch('bw.web_utils.load_template_from_disk', return_value='<p>{{ message }}</p>')
    mock_render_template.return_value = '<p>Saved</p>'

    response = await htmx_template_response('status.html', context={'message': 'Saved'}, retarget='#card', reswap='outerHTML')
    body = b''.join(await consume_generator(response)).decode()

    assert body == '<p>Saved</p>'
    assert response.headers['HX-Retarget'] == '#card'
    assert response.headers['HX-Reswap'] == 'outerHTML'
    mock_render_template.assert_called_once_with('<p>{{ message }}</p>', message='Saved')


# ==============================================================================
# UNIT UNDER TEST: htmx_redirect
# ==============================================================================


def test__htmx_redirect__uses_204_hx_redirect_for_htmx(mock_request, mocker):
    mocker.patch('bw.web_utils.has_request_context', return_value=True)
    mock_request.headers = {'HX-Request': 'true'}

    response = htmx_redirect('/auth/login')

    assert response.status_code == 204
    assert response.headers['HX-Redirect'] == '/auth/login'
    assert 'Location' not in response.headers


def test__htmx_redirect__uses_303_location_for_regular_request(mock_request, mocker):
    mocker.patch('bw.web_utils.has_request_context', return_value=True)
    mock_request.headers = {}

    response = htmx_redirect('/auth/login')

    assert response.status_code == 303
    assert response.headers['Location'] == '/auth/login'


# ==============================================================================
# UNIT UNDER TEST: is_htmx_partial_request
# ==============================================================================


def test__is_htmx_partial_request__true_for_targeted_htmx_request(mock_request, mocker):
    mocker.patch('bw.web_utils.has_request_context', return_value=True)
    mock_request.headers = {'HX-Request': 'true', 'HX-Request-Type': 'partial'}

    assert is_htmx_partial_request()


def test__is_htmx_partial_request__false_for_htmx_full_request(mock_request, mocker):
    mocker.patch('bw.web_utils.has_request_context', return_value=True)
    mock_request.headers = {'HX-Request': 'true', 'HX-Request-Type': 'full'}

    assert not is_htmx_partial_request()


def test__is_htmx_partial_request__false_for_boosted_request(mock_request, mocker):
    mocker.patch('bw.web_utils.has_request_context', return_value=True)
    mock_request.headers = {'HX-Request': 'true', 'HX-Boosted': 'true'}

    assert not is_htmx_partial_request()


# ==============================================================================
# UNIT UNDER TEST: html_endpoint
# ==============================================================================


@pytest.mark.asyncio
async def test__html_endpoint__renders_successful_template(mocker, mock_render_template):
    # Mock file reading to return predictable HTML content
    mocker.patch('bw.web_utils.load_template_from_disk', return_value='<html>{{inner}}</html>')
    mock_render_template.return_value = 'FINAL PAGE'

    @html_endpoint(template_path='dashboard.html', title='My Title')
    async def endpoint(html: str):
        return html.replace('{{inner}}', 'Success')

    result = b''.join(await consume_generator(await endpoint())).decode()

    assert result
    mock_render_template.assert_called_once()


@pytest.mark.asyncio
async def test__html_endpoint__renders_error_template_on_bw_server_error(mocker, mock_error, mock_render_template):
    mocker.patch('bw.web_utils.load_template_from_disk', return_value='Error Page HTML')
    mock_render_template.return_value = 'FINAL ERROR PAGE'

    @html_endpoint(template_path='dashboard.html')
    async def endpoint(html: str):
        raise mock_error

    result = b''.join(await consume_generator(await endpoint())).decode()

    assert result
    mock_render_template.assert_called_once()


@pytest.mark.asyncio
async def test__html_endpoint__passes_logged_in_when_endpoint_accepts_it(mocker):
    mocker.patch('bw.web_utils.load_template_from_disk', return_value='<html></html>')
    endpoint_spy = mocker.Mock()

    @html_endpoint(template_path='dashboard.html', return_partial=True)
    async def endpoint(html: str, logged_in: bool):
        endpoint_spy(logged_in)
        return ''

    await consume_generator(await endpoint())

    endpoint_spy.assert_called_once_with(False)


# ==============================================================================
# UNIT UNDER TEST: sse_endpoint
# ==============================================================================


@pytest.mark.asyncio
async def test__sse_endpoint__returns_error_if_wrong_accept_mimetype(mock_request, mocker):
    mocker.patch('bw.web_utils.WrongAccept')
    mocker.patch('bw.web_utils.ServerSentResponseError', return_value='Error Response')

    mock_request.accept_mimetypes = {'application/json': 'application/json'}

    @sse_endpoint
    async def endpoint():
        yield None

    assert await endpoint() == 'Error Response'


@pytest.mark.asyncio
async def test__sse_endpoint__yields_encoded_events_successfully(mock_request, mocker):
    mock_event = MagicMock()
    mock_event.encode.return_value = b'encoded_event_data'

    response_spy = MagicMock()
    mock_factory = mocker.patch('bw.web_utils.ServerSentEventResponse.from_async_generator', return_value=response_spy)

    @sse_endpoint
    async def endpoint():
        yield mock_event

    result = await endpoint()
    assert result is response_spy

    generator_func = mock_factory.call_args[0][0]

    chunks = [chunk async for chunk in generator_func()]
    assert chunks == [b'encoded_event_data']


# ==============================================================================
# UNIT UNDER TEST: unwrap_headers
# ==============================================================================


@pytest.mark.asyncio
async def test__unwrap_headers__extracts_and_casts_headers_correctly(mock_request):
    mock_request.headers = {'X-Api-Version': '1', 'Session-Id': 'abc'}

    @unwrap_headers(('X-Api-Version', int), ('Session-Id', str))
    async def endpoint(x_api_version: int, session_id: str):
        return (x_api_version, session_id)

    result = await endpoint()

    assert result == (1, 'abc')


@pytest.mark.asyncio
async def test__unwrap_headers__raises_bad_header_if_missing(mock_request, mocker):
    mock_request.headers = {}

    @unwrap_headers(('Missing-Header', str))
    async def endpoint(missing_header: str):
        return 'Should not reach here'

    with pytest.raises(BadHeader):
        await endpoint()


class CapturedResponse:
    def __init__(self, media_type: str, generator, headers):
        self.media_type = media_type
        self.generator = generator
        self.headers = headers


@pytest.fixture(autouse=True)
def patch_dependencies(mocker):
    """
    Automatically patches the system dependencies so we can capture the raw
    async generator and its output chunks safely.
    """
    mocker.patch('bw.converters.make_json_safe', side_effect=lambda x: x)
    return mocker.patch('bw.web_utils.ChunkedResponse.from_async_generator', side_effect=CapturedResponse)


async def consume_generator(response: CapturedResponse) -> list[bytes]:
    """Helper utility to extract all chunks out of the captured async generator."""
    chunks = []
    async for chunk in response.generator():
        chunks.append(chunk)
    return chunks


# ==============================================================================
# UNIT UNDER TEST: chunk_text_response
# ==============================================================================


@pytest.mark.asyncio
async def test__chunk_text_response__handles_empty_string():
    response = chunk_text_response('', max_chunk_size=5)

    chunks = await consume_generator(response)

    assert response.media_type == 'text/plain'
    assert chunks == []


@pytest.mark.asyncio
async def test__chunk_text_response__chunks_small_string_in_one_go():
    response = chunk_text_response('hello', max_chunk_size=10)

    chunks = await consume_generator(response)

    assert chunks == [b'hello']


@pytest.mark.asyncio
async def test__chunk_text_response__splits_large_string_into_chunks():
    response = chunk_text_response('abcdefghij', max_chunk_size=3)

    chunks = await consume_generator(response)

    assert chunks == [b'abc', b'def', b'ghi', b'j']


@pytest.mark.asyncio
async def test__chunk_text_response__passes_headers():
    test_headers = {'X-Test-Headers': 'true'}
    response = chunk_text_response('', headers=test_headers)
    assert response.headers == test_headers


# ==============================================================================
# UNIT UNDER TEST: chunk_json_response
# ==============================================================================


@pytest.mark.asyncio
async def test__chunk_json_response__handles_empty_iterable():
    response = chunk_json_response([], max_chunk_size=10)

    chunks = await consume_generator(response)

    assert response.media_type == 'application/x-ndjson'
    assert chunks == []


@pytest.mark.asyncio
async def test__chunk_json_response__flushes_remaining_buffer_at_end():
    # Individual rows encoded: b'{"a":1}\n' (8 bytes), b'{"b":2}\n' (8 bytes)
    # Total stream size = 16 bytes. Max chunk size = 50. Everything should be flushed at the end.
    data = [{'a': 1}, {'b': 2}]
    response = chunk_json_response(data, max_chunk_size=50)

    chunks = await consume_generator(response)

    assert chunks == [b'{"a": 1}\n{"b": 2}\n']


@pytest.mark.asyncio
async def test__chunk_json_response__clears_buffer_when_max_size_exceeded():
    # Each item is 8 bytes. Max chunk size is 10.
    # Item 1 added (buffer=8). Item 2 added (buffer=16 >= 10) -> Yields 16 bytes, flushes buffer.
    data = [{'a': 1}, {'b': 2}, {'c': 3}]
    response = chunk_json_response(data, max_chunk_size=10)

    chunks = await consume_generator(response)

    assert chunks == [b'{"a": 1}\n{"b": 2}\n', b'{"c": 3}\n']


@pytest.mark.asyncio
async def test__chunk_json_response__yields_buffer_then_oversized_row():
    # Tests the branch where an upcoming item is larger than max_chunk_size,
    # forcing the existing non-empty buffer to yield first to preserve ordering.
    data = [
        {'small': 1},  # 12 bytes (fits in buffer)
        {'huge': 'xxxxxxxxxxxxxxxxxxxx'},  # 33 bytes (exceeds max_chunk_size of 15)
    ]
    response = chunk_json_response(data, max_chunk_size=15)

    chunks = await consume_generator(response)

    assert chunks == [b'{"small": 1}\n', b'{"huge": "xxxxxxxxxxxxxxxxxxxx"}\n']


@pytest.mark.asyncio
async def test__chunk_json_response__yields_oversized_row_immediately_if_buffer_empty():
    # Tests the branch where an item is larger than max_chunk_size,
    # but the buffer is already empty. It shouldn't yield an empty byte chunk.
    data = [{'huge': 'xxxxxxxxxxxxxxxxxxxx'}]
    response = chunk_json_response(data, max_chunk_size=15)

    chunks = await consume_generator(response)

    assert chunks == [b'{"huge": "xxxxxxxxxxxxxxxxxxxx"}\n']


@pytest.mark.asyncio
async def test__chunk_json_response__passes_headers():
    data = [{'blah': '1234'}]
    test_headers = {'X-Test-Headers': 'true'}
    response = chunk_json_response(data, headers=test_headers)
    assert response.headers == test_headers


# ==============================================================================
# UNIT UNDER TEST: chunk_file_response
# ==============================================================================


@pytest.mark.asyncio
async def test__chunk_file_response__handles_empty_file():
    file_obj = io.BytesIO(b'')
    response = chunk_file_response(file_obj, chunk_size=5)

    chunks = await consume_generator(response)

    assert response.media_type == 'text/plain'
    assert chunks == []


@pytest.mark.asyncio
async def test__chunk_file_response__reads_and_encodes_text_file():
    file_obj = io.StringIO('abcdef')
    response = chunk_file_response(file_obj, chunk_size=2)

    chunks = await consume_generator(response)

    assert chunks == [b'ab', b'cd', b'ef']


@pytest.mark.asyncio
async def test__chunk_file_response__reads_binary_file():
    file_obj = io.BytesIO(b'abcdef')
    response = chunk_file_response(file_obj, chunk_size=2)

    chunks = await consume_generator(response)

    assert chunks == [b'ab', b'cd', b'ef']


@pytest.mark.asyncio
async def test__chunk_file_response__closes_file_on_completion():
    file_obj = io.BytesIO(b'data')
    response = chunk_file_response(file_obj, chunk_size=2)

    assert not file_obj.closed
    await consume_generator(response)

    # Asserting observed lifecycle behavior: file must be closed when generator completes
    assert file_obj.closed


@pytest.mark.asyncio
async def test__chunk_file_response__closes_file_on_error():
    file_obj = io.BytesIO(b'data')
    response = chunk_file_response(file_obj, chunk_size=2)

    # Force a failure inside the stream loop to check robustness of the finally block
    try:
        async with aclosing(response.generator()) as gen:
            async for _ in gen:
                raise RuntimeError('Simulated consumer crash')
    except RuntimeError:
        pass

    # Asserting observed lifecycle behavior: file must be closed even if streaming raises an exception
    assert file_obj.closed


@pytest.mark.asyncio
async def test__chunk_file_response__passes_headers():
    file_obj = io.BytesIO(b'data')
    test_headers = {'X-Test-Headers': 'true'}
    response = chunk_file_response(file_obj, headers=test_headers)
    assert response.headers == test_headers


@pytest.mark.asyncio
async def test__html_endpoint__error_page_uses_error_status(mocker, mock_error, mock_render_template):
    mocker.patch('bw.web_utils.load_template_from_disk', return_value='Error Page HTML')
    mock_render_template.return_value = 'FINAL ERROR PAGE'

    @html_endpoint(template_path='dashboard.html')
    async def endpoint(html: str):
        raise mock_error

    response = await endpoint()
    assert response.status_code == 500
