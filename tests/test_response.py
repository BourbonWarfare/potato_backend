import json

import pytest

from bw.error import BwServerError
from bw.response import (
    BadRequest,
    ChunkedResponse,
    Created,
    DoesNotExist,
    Exists,
    HtmlResponse,
    JsonResponse,
    NotFound,
    Ok,
    ServerSentEventResponse,
    ServerSentResponseError,
    WebEvent,
    WebResponse,
    WithState,
)


@pytest.mark.asyncio
async def test__json_response__supports_setting_json_values():
    response = JsonResponse({'mission': 'foobar'})

    response['creation_date_display'] = '2026-09-07 16:20'

    assert response['creation_date_display'] == '2026-09-07 16:20'
    assert json.loads(await response.get_data(as_text=True))['creation_date_display'] == '2026-09-07 16:20'


def test__web_response__raise_if_unsuccessful_returns_self_for_success():
    """Test that successful responses return themselves when raised."""
    # Not yet reviewed
    response = Ok()

    assert response.raise_if_unsuccessful() is response


def test__web_response__raise_if_unsuccessful_raises_unknown_error_for_failure():
    """Test that failed responses raise a generic server error when no exception is attached."""
    # Not yet reviewed
    response = NotFound()

    with pytest.raises(BwServerError):
        response.raise_if_unsuccessful()


def test__web_response__raise_if_unsuccessful_reraises_attached_exception():
    """Test that failed responses re-raise their attached exception."""
    # Not yet reviewed
    expected_exception = ValueError('boom')
    response = WebResponse(500, from_exception=expected_exception)

    with pytest.raises(ValueError) as exc_info:
        response.raise_if_unsuccessful()

    assert exc_info.value is expected_exception


def test__web_response__bool_reflects_success_status():
    """Test that WebResponse truthiness follows successful status codes."""
    # Not yet reviewed
    assert bool(Ok()) is True
    assert bool(Created()) is True
    assert bool(BadRequest()) is False
    assert bool(NotFound()) is False


def test__with_state__stores_state_and_response_data():
    """Test that WithState stores the supplied state while acting as a response."""
    # Not yet reviewed
    state = object()

    response = WithState(state, data='payload')

    assert response.state is state
    assert response.status_code == 200


def test__exists__truthiness_uses_exists_flag():
    """Test that Exists and DoesNotExist use their exists flag for truthiness."""
    # Not yet reviewed
    exists = Exists()
    does_not_exist = DoesNotExist()

    assert bool(exists) is True
    assert exists.status_code == 200
    assert bool(does_not_exist) is False
    assert does_not_exist.status_code == 409


def test__json_response__supports_get_and_key_errors():
    """Test that JsonResponse supports dictionary-like access."""
    # Not yet reviewed
    response = JsonResponse({'value': 1})

    assert response.get('value') == 1
    assert response.get('missing', 'default') == 'default'
    assert response['value'] == 1
    with pytest.raises(KeyError):
        _ = response['missing']


def test__json_response__uses_contained_status():
    """Test that JsonResponse status can be supplied by the payload contract."""
    # Not yet reviewed
    response = JsonResponse({'status': 201, 'created': True})

    assert response.status_code == 201
    assert response.contained_json == {'created': True}


def test__html_response__uses_html_content_type():
    """Test that HtmlResponse uses the HTML content type."""
    # Not yet reviewed
    response = HtmlResponse('')

    assert response.headers['Content-Type'].startswith('text/html')


def test__web_event__encodes_sse_protocol_fields():
    """Test that WebEvent encodes machine-readable SSE protocol fields."""
    # Not yet reviewed
    response = WebEvent(event='event-name', data={'value': 1}, id='event-id', retry=10)

    encoded = response.encode().decode('utf-8')

    assert 'id: event-id\n' in encoded
    assert 'event: event-name\n' in encoded
    assert 'data: {"value": 1}\n' in encoded
    assert 'retry: 10\n' in encoded


@pytest.mark.asyncio
async def test__server_sent_event_response__uses_async_generator():
    """Test that ServerSentEventResponse streams bytes from an async generator."""
    # Not yet reviewed

    async def generator():
        yield b'data'

    response = ServerSentEventResponse.from_async_generator(generator)

    assert response.status_code == 200
    assert response.timeout is None
    assert await response.get_data() == b'data'


@pytest.mark.asyncio
async def test__chunked_response__parses_json_lines():
    """Test that ChunkedResponse parses streamed JSON lines."""
    # Not yet reviewed

    async def generator():
        yield b'{"value": 1}\n'
        yield b'{"value": 2}\n'

    response = ChunkedResponse.from_async_generator('application/json', generator)

    assert await response.as_json_list() == [{'value': 1}, {'value': 2}]


@pytest.mark.asyncio
async def test__chunked_response__parses_string_lines():
    """Test that ChunkedResponse parses streamed string lines."""
    # Not yet reviewed

    async def generator():
        yield b'first\n'
        yield b'second\n'

    response = ChunkedResponse.from_async_generator('text/plain', generator)

    assert await response.as_str_list() == ['first', 'second']


def test__server_sent_response_error__uses_supplied_status():
    """Test that ServerSentResponseError uses the supplied error status."""
    # Not yet reviewed
    response = ServerSentResponseError(406)

    assert response.status_code == 406
    assert response.headers['Content-Type'].startswith('text/event-stream')
