import io
from contextlib import aclosing
import pytest

from unittest.mock import AsyncMock, MagicMock, mock_open

from bw.response import WebResponse, JsonResponse
from bw.web_utils import (
chunk_text_response, chunk_json_response, chunk_file_response,
    define_api, url_endpoint, json_endpoint, html_endpoint, sse_endpoint, unwrap_headers,
    
)
from bw.error import (BwServerError, JsonPayloadError, BadArguments, ExpectedJson, BadHeader, WrongAccept)


# ==============================================================================
# FIXTURES & MOCKS
# ==============================================================================

@pytest.fixture
def mock_request(mocker):
    """Mocks the quart.request context object."""
    request_mock = MagicMock()
    # Async mock for get_json()
    request_mock.get_json = AsyncMock(return_value=None)
    request_mock.headers = {}
    request_mock.accept_mimetypes = {"text/event-stream": "text/event-stream"}
    
    mocker.patch('bw.web_utils.request', request_mock)
    return request_mock

@pytest.fixture
def mock_render_template(mocker):
    """Mocks Quart's render_template_string."""
    return mocker.patch('bw.web_utils.render_template_string', new_callable=AsyncMock)

# Mock Response Classes to easily assert returns

class MockWebResponse(WebResponse):
    def __init__(self): pass

class MockJsonResponse(JsonResponse):
    def __init__(self): pass

class MockErrorResponse(WebResponse):
    def __init__(self):
        self._status = "500 INTERNAL SERVER ERROR"

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


# ==============================================================================
# UNIT UNDER TEST: json_endpoint
# ==============================================================================

@pytest.mark.asyncio
async def test__json_endpoint__merges_json_with_kwargs(mock_request):
    mock_request.get_json.return_value = {"age": 30}
    
    @json_endpoint
    async def endpoint(name: str, age: int):
        return MockJsonResponse()
        
    # 'name' comes from kwargs/routing, 'age' comes from JSON body
    await endpoint(name="Alice")
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
    mock_request.get_json.return_value = {"id": 2} # Clashes with kwarg "id"
    expected_error_response = MockErrorResponse()
    mocker.patch('bw.error.JsonPayloadError.as_response_code', return_value=expected_error_response)
    
    @json_endpoint
    async def endpoint(id: int):
        return MockJsonResponse()
        
    assert await endpoint(id=1) is expected_error_response


@pytest.mark.asyncio
async def test__json_endpoint__returns_bad_arguments_on_type_error(mock_request, mocker):
    mock_request.get_json.return_value = {"extra_arg": "whoops"}
    expected_error_response = MockErrorResponse()
    mocker.patch('bw.error.BadArguments.as_response_code', return_value=expected_error_response)
    
    @json_endpoint
    async def endpoint(required: str):
        # This will raise TypeError internally because `extra_arg` is passed but not expected
        pass
        
    assert await endpoint(required="test") is expected_error_response


@pytest.mark.asyncio
async def test__json_endpoint__catches_bw_server_error(mock_request, mock_error):
    mock_request.get_json.return_value = {}
    
    @json_endpoint
    async def endpoint():
        raise mock_error
        
    assert await endpoint() is mock_error.as_response_code()


# ==============================================================================
# UNIT UNDER TEST: html_endpoint
# ==============================================================================

@pytest.mark.asyncio
async def test__html_endpoint__renders_successful_template(mocker, mock_render_template):
    # Mock file reading to return predictable HTML content
    mocker.patch("builtins.open", mock_open(read_data="<html>{{inner}}</html>"))
    mock_render_template.return_value = "FINAL PAGE"
    
    @html_endpoint(template_path="dashboard.html", title="My Title")
    async def endpoint(html: str):
        return html.replace("{{inner}}", "Success")
        
    result = await endpoint()
    
    assert result == "FINAL PAGE"
    mock_render_template.assert_called_once_with(
        "<html>{{inner}}</html>", 
        inner_html="<html>Success</html>", 
        title="My Title"
    )


@pytest.mark.asyncio
async def test__html_endpoint__renders_error_template_on_bw_server_error(mocker, mock_error, mock_render_template):
    mocker.patch("builtins.open", mock_open(read_data="Error Page HTML"))
    mock_render_template.return_value = "FINAL ERROR PAGE"
    
    @html_endpoint(template_path="dashboard.html")
    async def endpoint(html: str):
        raise mock_error
        
    result = await endpoint()
    
    assert result == "FINAL ERROR PAGE"
    mock_render_template.assert_called_once_with(
        "Error Page HTML", 
        inner_html="Error Page HTML", 
        title="Bourbon Warfare"
    )


# ==============================================================================
# UNIT UNDER TEST: sse_endpoint
# ==============================================================================

@pytest.mark.asyncio
async def test__sse_endpoint__returns_error_if_wrong_accept_mimetype(mock_request, mocker):
    mocker.patch('bw.web_utils.WrongAccept')
    mocker.patch('bw.web_utils.ServerSentResponseError', return_value="Error Response")

    mock_request.accept_mimetypes = {"application/json": "application/json"}
    
    @sse_endpoint
    async def endpoint():
        yield None
        
    assert await endpoint() == "Error Response"


@pytest.mark.asyncio
async def test__sse_endpoint__yields_encoded_events_successfully(mock_request, mocker):
    mock_event = MagicMock()
    mock_event.encode.return_value = b"encoded_event_data"
    
    response_spy = MagicMock()
    mock_factory = mocker.patch('bw.web_utils.ServerSentEventResponse.from_async_generator', return_value=response_spy)
    
    @sse_endpoint
    async def endpoint():
        yield mock_event
        
    result = await endpoint()
    assert result is response_spy
    
    generator_func = mock_factory.call_args[0][0]
    
    chunks = [chunk async for chunk in generator_func()]
    assert chunks == [b"encoded_event_data"]


# ==============================================================================
# UNIT UNDER TEST: unwrap_headers
# ==============================================================================

@pytest.mark.asyncio
async def test__unwrap_headers__extracts_and_casts_headers_correctly(mock_request):
    mock_request.headers = {"X-Api-Version": "1", "Session-Id": "abc"}
    
    @unwrap_headers(("X-Api-Version", int), ("Session-Id", str))
    async def endpoint(x_api_version: int, session_id: str):
        return (x_api_version, session_id)
        
    result = await endpoint()
    
    assert result == (1, "abc")


@pytest.mark.asyncio
async def test__unwrap_headers__raises_bad_header_if_missing(mock_request, mocker):
    mock_request.headers = {}
    
    @unwrap_headers(("Missing-Header", str))
    async def endpoint(missing_header: str):
        return "Should not reach here"
        
    with pytest.raises(BadHeader):
        await endpoint()

class CapturedResponse:
    def __init__(self, media_type: str, generator):
        self.media_type = media_type
        self.generator = generator


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
    response = chunk_text_response("", max_chunk_size=5)
    
    chunks = await consume_generator(response)
    
    assert response.media_type == 'text/plain'
    assert chunks == []


@pytest.mark.asyncio
async def test__chunk_text_response__chunks_small_string_in_one_go():
    response = chunk_text_response("hello", max_chunk_size=10)
    
    chunks = await consume_generator(response)
    
    assert chunks == [b"hello"]


@pytest.mark.asyncio
async def test__chunk_text_response__splits_large_string_into_chunks():
    response = chunk_text_response("abcdefghij", max_chunk_size=3)
    
    chunks = await consume_generator(response)
    
    assert chunks == [b"abc", b"def", b"ghi", b"j"]


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
    data = [{"a": 1}, {"b": 2}]
    response = chunk_json_response(data, max_chunk_size=50)
    
    chunks = await consume_generator(response)
    
    assert chunks == [b'{"a": 1}\n{"b": 2}\n']


@pytest.mark.asyncio
async def test__chunk_json_response__clears_buffer_when_max_size_exceeded():
    # Each item is 8 bytes. Max chunk size is 10.
    # Item 1 added (buffer=8). Item 2 added (buffer=16 >= 10) -> Yields 16 bytes, flushes buffer.
    data = [{"a": 1}, {"b": 2}, {"c": 3}]
    response = chunk_json_response(data, max_chunk_size=10)
    
    chunks = await consume_generator(response)
    
    assert chunks == [b'{"a": 1}\n{"b": 2}\n', b'{"c": 3}\n']


@pytest.mark.asyncio
async def test__chunk_json_response__yields_buffer_then_oversized_row():
    # Tests the branch where an upcoming item is larger than max_chunk_size, 
    # forcing the existing non-empty buffer to yield first to preserve ordering.
    data = [
        {"small": 1},                     # 12 bytes (fits in buffer)
        {"huge": "xxxxxxxxxxxxxxxxxxxx"}  # 33 bytes (exceeds max_chunk_size of 15)
    ]
    response = chunk_json_response(data, max_chunk_size=15)
    
    chunks = await consume_generator(response)
    
    assert chunks == [b'{"small": 1}\n', b'{"huge": "xxxxxxxxxxxxxxxxxxxx"}\n']


@pytest.mark.asyncio
async def test__chunk_json_response__yields_oversized_row_immediately_if_buffer_empty():
    # Tests the branch where an item is larger than max_chunk_size,
    # but the buffer is already empty. It shouldn't yield an empty byte chunk.
    data = [{"huge": "xxxxxxxxxxxxxxxxxxxx"}]
    response = chunk_json_response(data, max_chunk_size=15)
    
    chunks = await consume_generator(response)
    
    assert chunks == [b'{"huge": "xxxxxxxxxxxxxxxxxxxx"}\n']


# ==============================================================================
# UNIT UNDER TEST: chunk_file_response
# ==============================================================================

@pytest.mark.asyncio
async def test__chunk_file_response__handles_empty_file():
    file_obj = io.BytesIO(b"")
    response = chunk_file_response(file_obj, chunk_size=5)
    
    chunks = await consume_generator(response)
    
    assert response.media_type == 'text/plain'
    assert chunks == []


@pytest.mark.asyncio
async def test__chunk_file_response__reads_and_encodes_text_file():
    file_obj = io.StringIO("abcdef")
    response = chunk_file_response(file_obj, chunk_size=2)
    
    chunks = await consume_generator(response)
    
    assert chunks == [b"ab", b"cd", b"ef"]


@pytest.mark.asyncio
async def test__chunk_file_response__reads_binary_file():
    file_obj = io.BytesIO(b"abcdef")
    response = chunk_file_response(file_obj, chunk_size=2)
    
    chunks = await consume_generator(response)
    
    assert chunks == [b"ab", b"cd", b"ef"]


@pytest.mark.asyncio
async def test__chunk_file_response__closes_file_on_completion():
    file_obj = io.BytesIO(b"data")
    response = chunk_file_response(file_obj, chunk_size=2)
    
    assert not file_obj.closed
    await consume_generator(response)
    
    # Asserting observed lifecycle behavior: file must be closed when generator completes
    assert file_obj.closed


@pytest.mark.asyncio
async def test__chunk_file_response__closes_file_on_error():
    file_obj = io.BytesIO(b"data")
    response = chunk_file_response(file_obj, chunk_size=2)
    
    # Force a failure inside the stream loop to check robustness of the finally block
    try:
        async with aclosing(response.generator()) as gen:
            async for _ in gen:
                raise RuntimeError("Simulated consumer crash")
    except RuntimeError:
        pass

    # Asserting observed lifecycle behavior: file must be closed even if streaming raises an exception
    assert file_obj.closed

